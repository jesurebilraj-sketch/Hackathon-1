"""
tests/test_assessments.py - Phase 5 Step 1 Tests for AI Assessment System.

Covers:
1. Model creation and persistence for Quiz, QuizQuestion, QuizSubmission, UserMastery
2. Model relationships (Course, Module, Lesson, Quiz, QuizQuestion, QuizSubmission, User, UserMastery)
3. Cascade deletion behavior (preventing orphan records)
4. Migration compatibility and idempotency
5. Student-facing schemas: STRICTLY NO leakage of correct_answer or explanation
6. Schema validation for generation, submission, feedback, and mastery models
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from sqlalchemy import inspect

from database.database import init_db, migrate_schema
from database.models import (
    User,
    Course,
    Module,
    Lesson,
    Quiz,
    QuizQuestion,
    QuizSubmission,
    UserMastery,
)
from api.quiz_schemas import (
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
from tests.conftest import TestingSessionLocal, test_engine


# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    """Provides an isolated database session for testing."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_base_hierarchy(db):
    """Creates teacher, student, course, module, and lesson."""
    teacher = User(name="Prof. Turing", email="turing@example.com", role="teacher")
    student = User(name="Alice Student", email="alice@example.com", role="student")
    db.add_all([teacher, student])
    db.commit()
    db.refresh(teacher)
    db.refresh(student)

    course = Course(
        title="Intro to Computing",
        description="Fundamentals of Computer Science",
        teacher_id=teacher.id,
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    module = Module(course_id=course.id, title="Module 1: Logic", order_number=1)
    db.add(module)
    db.commit()
    db.refresh(module)

    lesson = Lesson(
        module_id=module.id,
        title="Boolean Algebra",
        content="Logic gates and Boolean truth tables.",
        order_number=1,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)

    return teacher, student, course, module, lesson


# ---------------------------------------------------------------------------
# 1. Model Creation Tests
# ---------------------------------------------------------------------------

def test_quiz_model_creation(db_session):
    """Verifies that Quiz entity can be created and persisted with all required fields."""
    _, _, course, module, lesson = create_base_hierarchy(db_session)

    quiz = Quiz(
        title="Boolean Algebra Checkpoint",
        description="Test understanding of truth tables",
        course_id=course.id,
        module_id=module.id,
        lesson_id=lesson.id,
        quiz_type="lesson_quiz",
        passing_score_percentage=75,
        time_limit_minutes=15,
        is_fallback=False,
    )
    db_session.add(quiz)
    db_session.commit()
    db_session.refresh(quiz)

    assert quiz.id is not None
    assert quiz.title == "Boolean Algebra Checkpoint"
    assert quiz.course_id == course.id
    assert quiz.module_id == module.id
    assert quiz.lesson_id == lesson.id
    assert quiz.quiz_type == "lesson_quiz"
    assert quiz.passing_score_percentage == 75
    assert quiz.time_limit_minutes == 15
    assert quiz.is_fallback is False
    assert isinstance(quiz.created_at, datetime)
    assert "<Quiz" in repr(quiz)


def test_quiz_question_model_creation(db_session):
    """Verifies that QuizQuestion entity can be created with options JSON and metadata."""
    _, _, course, module, lesson = create_base_hierarchy(db_session)

    quiz = Quiz(
        title="Logic Gates Quiz",
        course_id=course.id,
        module_id=module.id,
        lesson_id=lesson.id,
    )
    db_session.add(quiz)
    db_session.commit()
    db_session.refresh(quiz)

    question = QuizQuestion(
        quiz_id=quiz.id,
        question_text="What is the output of an AND gate when inputs are 1 and 0?",
        question_type="multiple_choice",
        options=["0", "1", "Undefined", "High Impedance"],
        correct_answer="0",
        explanation="An AND gate outputs 1 only when both inputs are 1.",
        points=2,
        difficulty="easy",
        concept="AND Gate Truth Table",
        order_number=1,
    )
    db_session.add(question)
    db_session.commit()
    db_session.refresh(question)

    assert question.id is not None
    assert question.quiz_id == quiz.id
    assert question.question_text.startswith("What is the output")
    assert question.options == ["0", "1", "Undefined", "High Impedance"]
    assert question.correct_answer == "0"
    assert question.explanation.startswith("An AND gate")
    assert question.points == 2
    assert question.difficulty == "easy"
    assert question.concept == "AND Gate Truth Table"
    assert question.order_number == 1
    assert "<QuizQuestion" in repr(question)


def test_quiz_submission_model_creation(db_session):
    """Verifies that QuizSubmission entity records scores, answers JSON, and feedback JSON."""
    _, student, course, _, lesson = create_base_hierarchy(db_session)

    quiz = Quiz(title="Quick Check", course_id=course.id, lesson_id=lesson.id)
    db_session.add(quiz)
    db_session.commit()
    db_session.refresh(quiz)

    submission = QuizSubmission(
        quiz_id=quiz.id,
        user_id=student.id,
        score=8.0,
        max_score=10.0,
        percentage=80.0,
        passed=True,
        answers={"1": "0", "2": "True"},
        feedback=[
            {"question_id": 1, "is_correct": True, "points_earned": 5.0},
            {"question_id": 2, "is_correct": False, "points_earned": 3.0},
        ],
    )
    db_session.add(submission)
    db_session.commit()
    db_session.refresh(submission)

    assert submission.id is not None
    assert submission.quiz_id == quiz.id
    assert submission.user_id == student.id
    assert submission.score == 8.0
    assert submission.max_score == 10.0
    assert submission.percentage == 80.0
    assert submission.passed is True
    assert submission.answers["1"] == "0"
    assert len(submission.feedback) == 2
    assert isinstance(submission.submitted_at, datetime)
    assert "<QuizSubmission" in repr(submission)


def test_user_mastery_model_creation(db_session):
    """Verifies that UserMastery records tracking student concept mastery can be created."""
    _, student, course, _, lesson = create_base_hierarchy(db_session)

    mastery = UserMastery(
        user_id=student.id,
        course_id=course.id,
        lesson_id=lesson.id,
        concept="Boolean Algebra",
        mastery_score=85.5,
        attempts_count=2,
        status="proficient",
    )
    db_session.add(mastery)
    db_session.commit()
    db_session.refresh(mastery)

    assert mastery.id is not None
    assert mastery.user_id == student.id
    assert mastery.course_id == course.id
    assert mastery.lesson_id == lesson.id
    assert mastery.concept == "Boolean Algebra"
    assert mastery.mastery_score == 85.5
    assert mastery.attempts_count == 2
    assert mastery.status == "proficient"
    assert isinstance(mastery.updated_at, datetime)
    assert "<UserMastery" in repr(mastery)


# ---------------------------------------------------------------------------
# 2. Relationships & Cascade Behavior Tests
# ---------------------------------------------------------------------------

def test_course_module_lesson_quiz_relationships(db_session):
    """Verifies bidirectional relationships between Course, Module, Lesson, and Quiz."""
    _, _, course, module, lesson = create_base_hierarchy(db_session)

    quiz = Quiz(
        title="Comprehensive Quiz",
        course_id=course.id,
        module_id=module.id,
        lesson_id=lesson.id,
    )
    db_session.add(quiz)
    db_session.commit()
    db_session.refresh(quiz)

    # Check back-references
    assert quiz in course.quizzes
    assert quiz in module.quizzes
    assert quiz in lesson.quizzes

    assert quiz.course.id == course.id
    assert quiz.module.id == module.id
    assert quiz.lesson.id == lesson.id


def test_quiz_questions_and_submissions_relationships(db_session):
    """Verifies Quiz -> questions and Quiz -> submissions relationships."""
    _, student, course, _, lesson = create_base_hierarchy(db_session)

    quiz = Quiz(title="Relationship Quiz", course_id=course.id, lesson_id=lesson.id)
    db_session.add(quiz)
    db_session.commit()
    db_session.refresh(quiz)

    q1 = QuizQuestion(
        quiz_id=quiz.id,
        question_text="Q1?",
        options=["A", "B"],
        correct_answer="A",
        explanation="Exp 1",
        order_number=1,
    )
    q2 = QuizQuestion(
        quiz_id=quiz.id,
        question_text="Q2?",
        options=["C", "D"],
        correct_answer="C",
        explanation="Exp 2",
        order_number=2,
    )
    db_session.add_all([q1, q2])

    sub = QuizSubmission(
        quiz_id=quiz.id,
        user_id=student.id,
        score=2.0,
        max_score=2.0,
        percentage=100.0,
        passed=True,
        answers={"1": "A", "2": "C"},
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(quiz)

    assert len(quiz.questions) == 2
    assert quiz.questions[0].question_text == "Q1?"
    assert quiz.questions[1].question_text == "Q2?"
    assert len(quiz.submissions) == 1
    assert quiz.submissions[0].user_id == student.id

    # Back-populates from child
    assert q1.quiz.id == quiz.id
    assert sub.quiz.id == quiz.id
    assert sub in student.quiz_submissions


def test_user_mastery_relationships(db_session):
    """Verifies User -> mastery, Course -> mastery_records, Lesson -> mastery relationships."""
    _, student, course, _, lesson = create_base_hierarchy(db_session)

    mastery = UserMastery(
        user_id=student.id,
        course_id=course.id,
        lesson_id=lesson.id,
        concept="Truth Tables",
        mastery_score=90.0,
        status="mastered",
    )
    db_session.add(mastery)
    db_session.commit()
    db_session.refresh(student)
    db_session.refresh(course)
    db_session.refresh(lesson)

    assert mastery in student.mastery
    assert mastery in course.mastery_records
    assert mastery in lesson.mastery
    assert mastery.user.id == student.id
    assert mastery.course.id == course.id
    assert mastery.lesson.id == lesson.id


def test_quiz_delete_cascade_removes_questions_and_submissions(db_session):
    """
    CRITICAL REQUIREMENT:
    Deleting a Quiz must cascade and delete its QuizQuestions and QuizSubmissions,
    preventing any orphan question records.
    """
    _, student, course, _, lesson = create_base_hierarchy(db_session)

    quiz = Quiz(title="Doomed Quiz", course_id=course.id, lesson_id=lesson.id)
    db_session.add(quiz)
    db_session.commit()
    db_session.refresh(quiz)

    q = QuizQuestion(
        quiz_id=quiz.id,
        question_text="Will this be deleted?",
        options=["Yes", "No"],
        correct_answer="Yes",
        explanation="Cascade delete handles it.",
        order_number=1,
    )
    sub = QuizSubmission(
        quiz_id=quiz.id,
        user_id=student.id,
        score=1.0,
        max_score=1.0,
        percentage=100.0,
        passed=True,
        answers={"1": "Yes"},
    )
    db_session.add_all([q, sub])
    db_session.commit()

    q_id = q.id
    sub_id = sub.id

    # Delete the quiz
    db_session.delete(quiz)
    db_session.commit()

    # Verify child records were deleted (no orphans)
    assert db_session.query(QuizQuestion).filter_by(id=q_id).first() is None
    assert db_session.query(QuizSubmission).filter_by(id=sub_id).first() is None


def test_course_delete_cascade_removes_quizzes_and_mastery(db_session):
    """Deleting a Course must cascade and delete all associated Quizzes and UserMastery records."""
    _, student, course, _, lesson = create_base_hierarchy(db_session)

    quiz = Quiz(title="Course Quiz", course_id=course.id, lesson_id=lesson.id)
    mastery = UserMastery(
        user_id=student.id,
        course_id=course.id,
        concept="Binary Addition",
        mastery_score=70.0,
    )
    db_session.add_all([quiz, mastery])
    db_session.commit()

    quiz_id = quiz.id
    mastery_id = mastery.id

    db_session.delete(course)
    db_session.commit()

    assert db_session.query(Quiz).filter_by(id=quiz_id).first() is None
    assert db_session.query(UserMastery).filter_by(id=mastery_id).first() is None


# ---------------------------------------------------------------------------
# 3. Database Migration Compatibility Tests
# ---------------------------------------------------------------------------

def test_migration_compatibility_and_idempotency():
    """
    Verifies that init_db() and migrate_schema() execute smoothly and idempotently
    without errors on the active engine, and that all assessment tables are registered.
    """
    init_db(test_engine)
    migrate_schema(test_engine)

    inspector = inspect(test_engine)
    tables = inspector.get_table_names()

    assert "quizzes" in tables
    assert "quiz_questions" in tables
    assert "quiz_submissions" in tables
    assert "user_mastery" in tables

    # Verify columns exist
    quiz_cols = {col["name"] for col in inspector.get_columns("quizzes")}
    assert {"id", "title", "course_id", "quiz_type", "passing_score_percentage", "is_fallback"}.issubset(quiz_cols)

    qq_cols = {col["name"] for col in inspector.get_columns("quiz_questions")}
    assert {"id", "quiz_id", "question_text", "options", "correct_answer", "explanation", "concept"}.issubset(qq_cols)

    qs_cols = {col["name"] for col in inspector.get_columns("quiz_submissions")}
    assert {"id", "quiz_id", "user_id", "score", "max_score", "percentage", "passed", "answers"}.issubset(qs_cols)

    um_cols = {col["name"] for col in inspector.get_columns("user_mastery")}
    assert {"id", "user_id", "course_id", "mastery_score", "attempts_count", "status"}.issubset(um_cols)


# ---------------------------------------------------------------------------
# 4. Student Response DOES NOT Expose correct_answer or explanation
# ---------------------------------------------------------------------------

def test_student_question_response_conceals_answers_and_explanations(db_session):
    """
    CRITICAL SECURITY TEST:
    Verifies that QuizQuestionStudentResponse NEVER exposes `correct_answer` or `explanation`.
    """
    _, _, course, _, lesson = create_base_hierarchy(db_session)
    quiz = Quiz(title="Security Test Quiz", course_id=course.id, lesson_id=lesson.id)
    db_session.add(quiz)
    db_session.commit()
    db_session.refresh(quiz)

    question = QuizQuestion(
        quiz_id=quiz.id,
        question_text="What is the answer to life, the universe, and everything?",
        options=["40", "41", "42", "43"],
        correct_answer="42",
        explanation="According to the Hitchhiker's Guide to the Galaxy, the answer is 42.",
        points=5,
        difficulty="hard",
        concept="Deep Thought Calculation",
        order_number=1,
    )
    db_session.add(question)
    db_session.commit()
    db_session.refresh(question)

    # Convert ORM object to student response model
    student_q = QuizQuestionStudentResponse.model_validate(question)
    dumped_dict = student_q.model_dump()
    dumped_json = student_q.model_dump_json()

    # 1. Attributes must not exist on the schema
    assert not hasattr(student_q, "correct_answer")
    assert not hasattr(student_q, "explanation")

    # 2. Dictionary dump must NOT have sensitive keys
    assert "correct_answer" not in dumped_dict
    assert "explanation" not in dumped_dict

    # 3. JSON serialized string must NOT contain sensitive strings or keys
    assert "correct_answer" not in dumped_json
    assert "explanation" not in dumped_json
    assert "42" not in dumped_dict.values()  # 42 is in options list, but not as correct_answer
    assert "According to the Hitchhiker's Guide" not in dumped_json

    # 4. Safe fields must remain accessible
    assert dumped_dict["id"] == question.id
    assert dumped_dict["question_text"] == question.question_text
    assert dumped_dict["options"] == ["40", "41", "42", "43"]
    assert dumped_dict["points"] == 5
    assert dumped_dict["difficulty"] == "hard"
    assert dumped_dict["concept"] == "Deep Thought Calculation"


def test_student_quiz_response_conceals_answers_and_explanations(db_session):
    """
    CRITICAL SECURITY TEST:
    Verifies that the composite QuizStudentResponse model conceals answers and explanations
    for all embedded questions when serialized.
    """
    _, _, course, _, lesson = create_base_hierarchy(db_session)
    quiz = Quiz(
        title="Full Student Quiz",
        description="Solve all questions",
        course_id=course.id,
        lesson_id=lesson.id,
    )
    db_session.add(quiz)
    db_session.commit()
    db_session.refresh(quiz)

    q1 = QuizQuestion(
        quiz_id=quiz.id,
        question_text="Question 1 Prompt",
        options=["Option A", "Option B"],
        correct_answer="Option A",
        explanation="Secret explanation for Q1",
        order_number=1,
    )
    q2 = QuizQuestion(
        quiz_id=quiz.id,
        question_text="Question 2 Prompt",
        options=["Option C", "Option D"],
        correct_answer="Option D",
        explanation="Secret explanation for Q2",
        order_number=2,
    )
    db_session.add_all([q1, q2])
    db_session.commit()
    db_session.refresh(quiz)

    student_quiz = QuizStudentResponse.model_validate(quiz)
    quiz_dict = student_quiz.model_dump()
    quiz_json = student_quiz.model_dump_json()

    assert len(quiz_dict["questions"]) == 2
    for q_data in quiz_dict["questions"]:
        assert "correct_answer" not in q_data
        assert "explanation" not in q_data

    assert "correct_answer" not in quiz_json
    assert "Secret explanation for Q1" not in quiz_json
    assert "Secret explanation for Q2" not in quiz_json


def test_teacher_quiz_response_includes_answers_and_explanations(db_session):
    """Verifies that the teacher/detail schema intentionally includes correct answers and explanations."""
    _, _, course, _, lesson = create_base_hierarchy(db_session)
    quiz = Quiz(title="Teacher View Quiz", course_id=course.id, lesson_id=lesson.id)
    db_session.add(quiz)
    db_session.commit()
    db_session.refresh(quiz)

    q = QuizQuestion(
        quiz_id=quiz.id,
        question_text="What is 2+2?",
        options=["3", "4", "5"],
        correct_answer="4",
        explanation="Standard arithmetic.",
        order_number=1,
    )
    db_session.add(q)
    db_session.commit()
    db_session.refresh(quiz)

    detail_quiz = QuizDetailResponse.model_validate(quiz)
    detail_dict = detail_quiz.model_dump()

    assert len(detail_dict["questions"]) == 1
    assert detail_dict["questions"][0]["correct_answer"] == "4"
    assert detail_dict["questions"][0]["explanation"] == "Standard arithmetic."


# ---------------------------------------------------------------------------
# 5. Schema Validation & Edge Cases Tests
# ---------------------------------------------------------------------------

def test_quiz_generate_request_validation():
    """Tests validation constraints on QuizGenerateRequest."""
    # Valid defaults
    req = QuizGenerateRequest(course_id=1)
    assert req.course_id == 1
    assert req.num_questions == 5
    assert req.difficulty == "medium"
    assert req.passing_score_percentage == 70
    assert req.quiz_type == "lesson_quiz"

    # Valid custom values
    custom_req = QuizGenerateRequest(
        course_id=1,
        module_id=2,
        lesson_id=3,
        quiz_type="module_quiz",
        title="Custom Quiz",
        num_questions=10,
        difficulty="hard",
        time_limit_minutes=30,
        passing_score_percentage=80,
    )
    assert custom_req.num_questions == 10
    assert custom_req.passing_score_percentage == 80

    # Boundary check: num_questions must be >= 1
    with pytest.raises(ValidationError):
        QuizGenerateRequest(course_id=1, num_questions=0)

    # Boundary check: num_questions must be <= 30
    with pytest.raises(ValidationError):
        QuizGenerateRequest(course_id=1, num_questions=31)

    # Boundary check: passing_score_percentage must be <= 100
    with pytest.raises(ValidationError):
        QuizGenerateRequest(course_id=1, passing_score_percentage=101)


def test_quiz_submission_request_and_result_validation():
    """Tests validation and structure of submission requests, question feedback, and results."""
    # Submission request
    sub_req = QuizSubmissionRequest(user_id=42, answers={"1": "Option A", "2": "Option B"})
    assert sub_req.user_id == 42
    assert sub_req.answers["1"] == "Option A"

    with pytest.raises(ValidationError):
        QuizSubmissionRequest(user_id="not_an_int", answers={})

    # Question feedback
    fb = QuizQuestionFeedback(
        question_id=1,
        question_text="What is a compiler?",
        user_answer="Translates high-level code",
        correct_answer="Translates high-level code to machine code",
        is_correct=True,
        points_earned=1.0,
        points_possible=1.0,
        explanation="Compilers convert source code to executable binaries.",
        concept="Compilation",
    )
    assert fb.is_correct is True
    assert fb.points_earned == 1.0

    # Submission result
    result = QuizSubmissionResultResponse(
        id=10,
        quiz_id=1,
        user_id=42,
        score=1.0,
        max_score=1.0,
        percentage=100.0,
        passed=True,
        answers={"1": "Translates high-level code"},
        feedback=[fb],
        submitted_at=datetime.utcnow(),
    )
    assert result.passed is True
    assert len(result.feedback) == 1
    assert result.feedback[0].concept == "Compilation"


def test_mastery_response_validation():
    """Tests validation of MasteryResponse and UserMasterySummaryResponse."""
    record = MasteryResponse(
        id=1,
        user_id=5,
        course_id=1,
        lesson_id=2,
        concept="Logic Gates",
        mastery_score=92.5,
        attempts_count=3,
        status="mastered",
        updated_at=datetime.utcnow(),
    )
    assert record.concept == "Logic Gates"
    assert record.status == "mastered"
    assert record.mastery_score == 92.5

    summary = UserMasterySummaryResponse(
        user_id=5,
        course_id=1,
        overall_mastery_score=92.5,
        mastery_records=[record],
    )
    assert summary.overall_mastery_score == 92.5
    assert len(summary.mastery_records) == 1
