"""
api/quizzes.py - AI Assessment & Grading Endpoints.

Provides REST APIs for:
- POST /api/quizzes/generate/lesson/{lesson_id}: Generates an AI multiple-choice assessment
  grounded in lesson content with deterministic offline fallback and idempotent updates.
- GET /api/quizzes/lesson/{lesson_id}: Retrieves student quiz for a lesson (zero answer leakage).
- GET /api/quizzes/{quiz_id}: Retrieves student quiz by quiz ID (zero answer leakage).
- GET /api/quizzes/{quiz_id}/detail: Retrieves full instructor/detail quiz (with answers and explanations).
- POST /api/quizzes/{quiz_id}/submit: Submits student answers, executes server-side automatic grading,
  persists QuizSubmission atomically, and returns itemized feedback and scores.
- GET /api/quizzes/{quiz_id}/submissions: Retrieves submission history for a quiz, optionally
  filtered by user_id.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import Quiz, QuizQuestion, QuizSubmission, User, Lesson, Module, Course
from ai.quiz_generator import generate_quiz_content, GeneratedQuiz
from ai.mastery import update_user_mastery_for_submission
from .quiz_schemas import (
    QuizGenerateRequest,
    QuizQuestionStudentResponse,
    QuizStudentResponse,
    QuizQuestionDetailResponse,
    QuizDetailResponse,
    QuizSubmissionRequest,
    QuizQuestionFeedback,
    QuizSubmissionResultResponse,
    MasteryResponse,
    UserMasterySummaryResponse,
)

logger = logging.getLogger("lms.api.quizzes")

router = APIRouter(prefix="/api/quizzes", tags=["Quizzes"])


@router.get("/", summary="Quiz endpoint index")
def list_quizzes():
    return {"message": "AI Assessment and Quiz API is operational."}


# ---------------------------------------------------------------------------
# Quiz Generation & Retrieval Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/generate/lesson/{lesson_id}",
    response_model=QuizStudentResponse,
    summary="Generate grounded AI assessment for a lesson",
    description="Generates an AI multiple-choice quiz grounded in the lesson content. "
                "Falls back deterministically to offline generation if Gemini is unavailable. "
                "Idempotently updates existing quizzes in-place without duplicating records.",
)
def generate_quiz_for_lesson(
    lesson_id: int,
    request: Optional[QuizGenerateRequest] = None,
    db: Session = Depends(get_db),
):
    """
    1. Loads the lesson and verifies existence.
    2. Validates that the lesson has usable educational content.
    3. Gathers all lesson pedagogical components.
    4. Invokes AI/deterministic quiz generation.
    5. Stores the quiz and questions idempotently and atomically in the database.
    6. Returns student-safe quiz (no answer or explanation leakage).
    """
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        logger.warning("Quiz generation failed: Lesson %d not found.", lesson_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lesson with ID {lesson_id} not found.",
        )

    has_content = bool(lesson.content and lesson.content.strip())
    has_concepts = bool(lesson.key_concepts and len(lesson.key_concepts) > 0)
    has_practice = bool(lesson.practice_questions and len(lesson.practice_questions) > 0)
    has_summary = bool(lesson.summary and lesson.summary.strip())

    if not (has_content or has_concepts or has_practice or has_summary):
        logger.warning("Quiz generation failed: Lesson %d has no educational content.", lesson_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lesson '{lesson.title}' has no usable educational content. "
                   "Please generate lesson content before generating an assessment.",
        )

    module = lesson.module
    course = module.course if module else None
    req = request or QuizGenerateRequest()

    course_id = course.id if course else (req.course_id or 1)

    content = lesson.content or ""
    summary = lesson.summary or ""
    learning_objectives = lesson.learning_objectives or []
    key_concepts = lesson.key_concepts or []
    examples = lesson.examples or []
    misconceptions = lesson.misconceptions or []
    practice_questions = lesson.practice_questions or []

    logger.info("Generating quiz for lesson %d ('%s')...", lesson.id, lesson.title)
    generated: GeneratedQuiz = generate_quiz_content(
        lesson_title=lesson.title,
        module_title=module.title if module else None,
        course_title=course.title if course else None,
        content=content,
        summary=summary,
        learning_objectives=learning_objectives,
        key_concepts=key_concepts,
        examples=examples,
        misconceptions=misconceptions,
        practice_questions=practice_questions,
        num_questions=req.num_questions,
        difficulty=req.difficulty,
        passing_score_percentage=req.passing_score_percentage,
        time_limit_minutes=req.time_limit_minutes,
    )

    try:
        existing_quiz = db.query(Quiz).filter(Quiz.lesson_id == lesson.id).first()
        quiz_title = req.title or generated.title or f"Quiz: {lesson.title}"
        quiz_desc = generated.description or f"Assessment of understanding for '{lesson.title}'"

        if existing_quiz:
            logger.info("Regenerating existing quiz ID %d for lesson %d in-place.", existing_quiz.id, lesson.id)
            for old_q in list(existing_quiz.questions):
                db.delete(old_q)
            db.flush()

            existing_quiz.title = quiz_title
            existing_quiz.description = quiz_desc
            existing_quiz.passing_score_percentage = req.passing_score_percentage
            existing_quiz.time_limit_minutes = req.time_limit_minutes
            existing_quiz.quiz_type = req.quiz_type
            existing_quiz.is_fallback = generated.is_fallback
            quiz = existing_quiz
        else:
            logger.info("Creating new quiz for lesson %d.", lesson.id)
            quiz = Quiz(
                title=quiz_title,
                description=quiz_desc,
                course_id=course_id,
                module_id=lesson.module_id,
                lesson_id=lesson.id,
                quiz_type=req.quiz_type,
                passing_score_percentage=req.passing_score_percentage,
                time_limit_minutes=req.time_limit_minutes,
                is_fallback=generated.is_fallback,
            )
            db.add(quiz)
            db.flush()

        for idx, q in enumerate(generated.questions, start=1):
            question_entry = QuizQuestion(
                quiz_id=quiz.id,
                question_text=q.question_text,
                question_type=q.question_type,
                options=q.options,
                correct_answer=q.correct_answer,
                explanation=q.explanation,
                points=q.points,
                difficulty=q.difficulty,
                concept=q.concept,
                order_number=idx,
            )
            db.add(question_entry)

        db.commit()
        db.refresh(quiz)
        logger.info("Quiz successfully saved (ID: %d, %d questions, is_fallback=%s).",
                    quiz.id, len(quiz.questions), quiz.is_fallback)

    except Exception as exc:
        db.rollback()
        logger.error("Failed to persist quiz for lesson %d: %s", lesson_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist generated quiz: {str(exc)}",
        )

    return QuizStudentResponse.model_validate(quiz)


@router.get(
    "/lesson/{lesson_id}",
    response_model=QuizStudentResponse,
    summary="Get student quiz for a lesson",
    description="Returns the student-safe assessment for a lesson without exposing answers or explanations.",
)
def get_quiz_for_lesson(lesson_id: int, db: Session = Depends(get_db)):
    quiz = db.query(Quiz).filter(Quiz.lesson_id == lesson_id).first()
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No quiz found for lesson {lesson_id}. Please generate one first.",
        )
    return QuizStudentResponse.model_validate(quiz)


@router.get(
    "/{quiz_id}",
    response_model=QuizStudentResponse,
    summary="Get student quiz by ID",
    description="Returns the student-safe assessment by quiz ID without exposing answers or explanations.",
)
def get_quiz_by_id(quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with ID {quiz_id} not found.",
        )
    return QuizStudentResponse.model_validate(quiz)


@router.get(
    "/{quiz_id}/detail",
    response_model=QuizDetailResponse,
    summary="Get instructor detail quiz by ID",
    description="Returns the complete assessment including correct answers and pedagogical explanations for instructors.",
)
def get_quiz_detail(quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with ID {quiz_id} not found.",
        )
    return QuizDetailResponse.model_validate(quiz)


# ---------------------------------------------------------------------------
# Quiz Submission & Grading Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/{quiz_id}/submit",
    response_model=QuizSubmissionResultResponse,
    summary="Submit quiz answers for automatic grading",
    description="Grades submitted answers server-side against stored questions, "
                "creates an itemized evaluation, calculates percentage and pass/fail status, "
                "and atomically saves the submission.",
)
def submit_quiz(
    quiz_id: int,
    request: QuizSubmissionRequest,
    db: Session = Depends(get_db),
):
    """
    1. Validates quiz exists (404).
    2. Validates student user exists (404).
    3. Loads all questions for the quiz. Rejects empty quizzes (400).
    4. Validates submitted answers:
       - Rejects unknown question IDs (400).
       - Rejects invalid choices not in question.options (400).
       - Explicitly handles missing answers as 0 points.
    5. Grades each question server-side against stored correct_answer:
       - Awards question.points when correct.
       - Awards 0 when incorrect.
       - Calculates total score, max score, percentage, and passed status.
    6. Creates and atomically commits QuizSubmission.
    7. Returns graded QuizSubmissionResultResponse with itemized feedback.
    """
    # 1. Validate Quiz exists
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        logger.warning("Quiz submission rejected: Quiz %d not found.", quiz_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with ID {quiz_id} not found.",
        )

    # 2. Validate User exists
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        logger.warning("Quiz submission rejected: User %d not found.", request.user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {request.user_id} not found.",
        )

    # 3. Load all questions belonging to the quiz
    questions = list(quiz.questions)
    if not questions:
        logger.warning("Quiz submission rejected: Quiz %d has no questions.", quiz_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quiz {quiz_id} contains no questions and cannot be graded.",
        )

    questions_by_str_id: Dict[str, QuizQuestion] = {str(q.id): q for q in questions}

    # 4. Validate submitted answers
    for q_id_key, submitted_ans in request.answers.items():
        # Reject unknown question IDs
        if str(q_id_key) not in questions_by_str_id:
            logger.warning("Quiz submission rejected: Question ID '%s' not in quiz %d.", q_id_key, quiz_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid question ID '{q_id_key}'. Question does not belong to quiz {quiz_id}.",
            )

        # Reject options not among the question's 4 options
        if submitted_ans is not None and str(submitted_ans).strip() != "":
            q_obj = questions_by_str_id[str(q_id_key)]
            valid_opts = [str(opt).strip() for opt in (q_obj.options or [])]
            submitted_str = str(submitted_ans).strip()
            matched = any(opt == submitted_str or opt.lower() == submitted_str.lower() for opt in valid_opts)
            if not matched:
                logger.warning(
                    "Quiz submission rejected: Option '%s' not in question %d options: %s",
                    submitted_ans, q_obj.id, valid_opts,
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid option '{submitted_ans}' for question {q_obj.id}. "
                           f"Must be one of: {valid_opts}.",
                )

    # 5. Grade each question server-side
    feedback_items: List[QuizQuestionFeedback] = []
    total_score = 0.0
    max_score = 0.0

    for q in questions:
        q_pts = float(q.points) if q.points is not None else 1.0
        max_score += q_pts

        raw_submitted = request.answers.get(str(q.id))
        if raw_submitted is None and q.id in request.answers:
            raw_submitted = request.answers[q.id]

        if raw_submitted is None or str(raw_submitted).strip() == "":
            # Explicitly handled missing answer
            user_answer = None
            is_correct = False
            points_earned = 0.0
        else:
            user_answer = str(raw_submitted).strip()
            correct_clean = q.correct_answer.strip()
            is_correct = (user_answer == correct_clean) or (user_answer.lower() == correct_clean.lower())
            points_earned = q_pts if is_correct else 0.0

        total_score += points_earned

        fb = QuizQuestionFeedback(
            question_id=q.id,
            question_text=q.question_text,
            user_answer=user_answer,
            correct_answer=q.correct_answer,
            is_correct=is_correct,
            points_earned=points_earned,
            points_possible=q_pts,
            explanation=q.explanation,
            concept=q.concept,
        )
        feedback_items.append(fb)

    percentage = round((total_score / max_score) * 100.0, 2) if max_score > 0 else 0.0
    passing_threshold = float(quiz.passing_score_percentage if quiz.passing_score_percentage is not None else 70)
    passed = percentage >= passing_threshold

    # 6. Atomically persist QuizSubmission
    try:
        submission = QuizSubmission(
            quiz_id=quiz.id,
            user_id=user.id,
            score=total_score,
            max_score=max_score,
            percentage=percentage,
            passed=passed,
            answers=request.answers,
            feedback=[fb.model_dump() for fb in feedback_items],
            submitted_at=datetime.utcnow(),
        )
        db.add(submission)
        db.flush()

        # Update or create concept mastery records atomically
        update_user_mastery_for_submission(
            db=db,
            user_id=user.id,
            course_id=quiz.course_id,
            lesson_id=quiz.lesson_id,
            feedback_items=feedback_items,
        )

        db.commit()
        db.refresh(submission)
        logger.info(
            "Quiz submission and mastery saved successfully (ID: %d, user: %d, score: %.1f/%.1f, %.1f%%, passed=%s).",
            submission.id, user.id, total_score, max_score, percentage, passed,
        )
    except Exception as exc:
        db.rollback()
        logger.error("Failed to persist quiz submission or mastery for quiz %d: %s", quiz_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error saving quiz submission: {str(exc)}",
        )

    # 7. Return graded response with itemized feedback
    return QuizSubmissionResultResponse(
        id=submission.id,
        quiz_id=submission.quiz_id,
        user_id=submission.user_id,
        score=submission.score,
        max_score=submission.max_score,
        percentage=submission.percentage,
        passed=submission.passed,
        answers=submission.answers or {},
        feedback=feedback_items,
        submitted_at=submission.submitted_at,
    )


@router.get(
    "/{quiz_id}/submissions",
    response_model=List[QuizSubmissionResultResponse],
    summary="Get quiz submission history",
    description="Returns submission records for a quiz, optionally filtered by student user_id.",
)
def get_quiz_submissions(
    quiz_id: int,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Retrieves the submission history for a quiz.
    Supports user_id filtering so students only view their own submissions.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz with ID {quiz_id} not found.",
        )

    query = db.query(QuizSubmission).filter(QuizSubmission.quiz_id == quiz_id)
    if user_id is not None:
        query = query.filter(QuizSubmission.user_id == user_id)

    submissions = query.order_by(QuizSubmission.submitted_at.desc()).all()

    results: List[QuizSubmissionResultResponse] = []
    for sub in submissions:
        fb_list = None
        if sub.feedback:
            fb_list = [QuizQuestionFeedback.model_validate(f) for f in sub.feedback]
        results.append(
            QuizSubmissionResultResponse(
                id=sub.id,
                quiz_id=sub.quiz_id,
                user_id=sub.user_id,
                score=sub.score,
                max_score=sub.max_score,
                percentage=sub.percentage,
                passed=sub.passed,
                answers=sub.answers or {},
                feedback=fb_list,
                submitted_at=sub.submitted_at,
            )
        )
    return results
