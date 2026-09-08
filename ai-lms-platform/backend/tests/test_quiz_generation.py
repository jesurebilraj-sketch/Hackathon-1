"""
tests/test_quiz_generation.py - Phase 5 Step 2 Tests: AI Assessment Generation.

Covers:
1. Gemini quiz generation with mocked LLM.
2. Correct Pydantic/LLM output validation.
3. Exactly 4 options per question.
4. Exactly 1 correct answer per question.
5. Correct answer belongs to options.
6. Duplicate question prevention.
7. Fallback generation when Gemini raises LLMError.
8. Fallback generation when quota/429 occurs.
9. is_fallback flag behavior (False for Gemini, True for fallback).
10. Lesson-not-found behavior (404).
11. Missing lesson content behavior (400).
12. Quiz regeneration is idempotent.
13. No duplicate quizzes/questions after regeneration.
14. Full student response does not leak answers/explanations.
15. Instructor detail view preserves answers/explanations.
"""

import pytest
from unittest.mock import patch
from pydantic import ValidationError

from database.models import User, Course, Module, Lesson, Quiz, QuizQuestion
from ai.llm_client import LLMError, LLMResponseError
from ai.quiz_generator import (
    GeneratedQuestion,
    GeneratedQuiz,
    generate_grounded_fallback_quiz,
    generate_quiz_content,
)
from tests.conftest import TestingSessionLocal


@pytest.fixture
def test_db():
    """Provides an isolated database session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_lesson_with_content(db) -> Lesson:
    """Helper creating a complete hierarchy with rich educational lesson content."""
    teacher = User(name="Dr. Smith", email="smith@university.edu", role="teacher")
    db.add(teacher)
    db.commit()
    db.refresh(teacher)

    course = Course(
        title="Workplace Safety & Compliance",
        description="Comprehensive compliance training",
        teacher_id=teacher.id,
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    module = Module(course_id=course.id, title="Module 1: Workplace Standards", order_number=1)
    db.add(module)
    db.commit()
    db.refresh(module)

    lesson = Lesson(
        module_id=module.id,
        title="Preventing Harassment and Discrimination",
        content=(
            "Harassment in the workplace includes unwelcome verbal, visual, or physical conduct. "
            "Hostile work environment claims require severe or pervasive conduct that alters employment conditions. "
            "Retaliation against an employee who files a report is strictly prohibited by law. "
            "Employers must maintain an active, confidential reporting procedure to investigate grievances. "
            "Protected characteristics include race, gender, age, religion, and disability."
        ),
        summary="A thorough guide to identifying, reporting, and preventing harassment and hostile environments.",
        learning_objectives=[
            "Identify behaviors that constitute hostile work environments",
            "Explain non-retaliation protections for reporting employees",
            "Differentiate between severe and pervasive conduct",
        ],
        key_concepts=[
            "Hostile Work Environment",
            "Retaliation Protection",
            "Protected Characteristics",
            "Severe or Pervasive Standard",
        ],
        examples=[
            "A manager demoting an employee after they report misconduct is an example of illegal retaliation.",
            "Repeated offensive comments that persist after objection constitute a hostile work environment.",
        ],
        misconceptions=[
            "Conduct is only harassment if physical contact occurs.",
            "A single isolated minor joke always establishes a legal hostile work environment.",
            "Independent contractors cannot be protected under workplace anti-harassment policies.",
        ],
        practice_questions=[
            {
                "question": "What standard must be met to establish a hostile work environment?",
                "answer": "The conduct must be severe or pervasive enough to alter the conditions of employment.",
                "explanation": "Legal standards require conduct to be severe or pervasive, not merely an isolated trivial remark.",
            },
            {
                "question": "Which of the following actions is classified as illegal retaliation?",
                "answer": "Demoting an employee because they participated in an investigation.",
                "explanation": "Adverse employment actions taken in response to protected reporting activities constitute retaliation.",
            },
        ],
        order_number=1,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


# ---------------------------------------------------------------------------
# 1. Pydantic / LLM Output Validation Unit Tests
# ---------------------------------------------------------------------------

def test_generated_question_requires_exactly_4_options():
    """Verify that GeneratedQuestion enforces exactly 4 choices."""
    # 3 options -> raises error
    with pytest.raises(ValidationError):
        GeneratedQuestion(
            question_text="What is 2+2?",
            options=["1", "2", "4"],
            correct_answer="4",
            explanation="Basic addition",
        )

    # 5 options -> raises error
    with pytest.raises(ValidationError):
        GeneratedQuestion(
            question_text="What is 2+2?",
            options=["1", "2", "3", "4", "5"],
            correct_answer="4",
            explanation="Basic addition",
        )

    # Exactly 4 options -> succeeds
    q = GeneratedQuestion(
        question_text="What is 2+2?",
        options=["1", "2", "3", "4"],
        correct_answer="4",
        explanation="Basic addition",
    )
    assert len(q.options) == 4


def test_generated_question_requires_unique_options():
    """Verify that GeneratedQuestion rejects duplicate options."""
    with pytest.raises(ValidationError):
        GeneratedQuestion(
            question_text="Select the unique value",
            options=["Alpha", "Beta", "alpha", "Gamma"],  # "Alpha" and "alpha" are duplicates
            correct_answer="Beta",
            explanation="Duplicates are disallowed",
        )


def test_generated_question_correct_answer_must_belong_to_options():
    """Verify that correct_answer must exist within options."""
    with pytest.raises(ValidationError):
        GeneratedQuestion(
            question_text="What is the capital of France?",
            options=["Berlin", "Madrid", "Rome", "Lisbon"],
            correct_answer="Paris",  # Not in options
            explanation="Paris is the capital of France.",
        )

    # Valid answer belonging to options
    q = GeneratedQuestion(
        question_text="What is the capital of France?",
        options=["Berlin", "Madrid", "Rome", "Paris"],
        correct_answer="Paris",
        explanation="Paris is the capital of France.",
    )
    assert q.correct_answer == "Paris"


def test_generated_quiz_duplicate_question_prevention():
    """Verify that duplicate questions are prevented and filtered."""
    q1 = GeneratedQuestion(
        question_text="What is an algorithm?",
        options=["Step by step instructions", "A programming language", "A computer chip", "An internet protocol"],
        correct_answer="Step by step instructions",
        explanation="An algorithm is a step by step procedure.",
        order_number=1,
    )
    q2 = GeneratedQuestion(
        question_text="What is an algorithm?",  # Duplicate prompt
        options=["Step by step instructions", "A programming language", "A computer chip", "An internet protocol"],
        correct_answer="Step by step instructions",
        explanation="Duplicate question explanation.",
        order_number=2,
    )
    q3 = GeneratedQuestion(
        question_text="What is a variable?",
        options=["A named storage location", "A mathematical constant", "A hardware device", "A network wire"],
        correct_answer="A named storage location",
        explanation="A variable holds data in memory.",
        order_number=3,
    )

    quiz = GeneratedQuiz(
        title="Computer Science Basics",
        questions=[q1, q2, q3],
    )
    # The duplicate should be filtered out, leaving 2 unique questions with re-indexed order numbers
    assert len(quiz.questions) == 2
    assert quiz.questions[0].order_number == 1
    assert quiz.questions[1].order_number == 2
    assert quiz.questions[1].question_text == "What is a variable?"


# ---------------------------------------------------------------------------
# 2. Deterministic Fallback Quiz Generation Tests
# ---------------------------------------------------------------------------

def test_deterministic_fallback_generator_rules():
    """
    Verifies that the offline deterministic generator:
    - produces requested number of questions
    - has exactly 4 options per question
    - exactly 1 correct answer matching options
    - produces plausible distractors
    - sets is_fallback=True
    """
    quiz = generate_grounded_fallback_quiz(
        lesson_title="Workplace Rights",
        content="Employees have a legal right to a safe workplace free from retaliation.",
        summary="A summary of workplace rights and regulations.",
        learning_objectives=["Understand non-retaliation rights", "Identify safe conditions"],
        key_concepts=["Retaliation", "Whistleblower Protection", "Safety Standards"],
        misconceptions=["Retaliation only counts if it involves direct termination."],
        practice_questions=[
            {
                "question": "What is whistleblower protection?",
                "answer": "Legal safeguards shielding workers who disclose illegal practices.",
                "explanation": "Whistleblower laws prevent adverse employment action against reporters.",
            }
        ],
        num_questions=4,
        difficulty="medium",
    )

    assert quiz.is_fallback is True
    assert len(quiz.questions) == 4

    for idx, q in enumerate(quiz.questions, start=1):
        assert q.order_number == idx
        assert len(q.options) == 4
        assert len(set(o.lower() for o in q.options)) == 4, f"Options not unique in Q{idx}: {q.options}"
        assert q.correct_answer in q.options, f"Correct answer '{q.correct_answer}' not in {q.options}"
        assert len(q.explanation) >= 5
        assert q.difficulty == "medium"
        assert q.concept is not None


# ---------------------------------------------------------------------------
# 3. Gemini Generation & Fallback End-to-End Tests
# ---------------------------------------------------------------------------

def test_gemini_quiz_generation_mocked_success(client, test_db):
    """Verifies that successful Gemini generation creates a quiz with is_fallback=False."""
    lesson = seed_lesson_with_content(test_db)

    mock_gemini_response = {
        "title": f"Quiz: {lesson.title}",
        "description": "Assessment generated by Gemini AI",
        "quiz_type": "lesson_quiz",
        "passing_score_percentage": 75,
        "questions": [
            {
                "question_text": "What does retaliation protection guarantee for an employee?",
                "question_type": "multiple_choice",
                "options": [
                    "Protection against adverse employment action for reporting violations",
                    "Guaranteed annual pay raises regardless of performance",
                    "Immunity from all company disciplinary actions forever",
                    "Automatic promotion to supervisory roles upon request",
                ],
                "correct_answer": "Protection against adverse employment action for reporting violations",
                "explanation": "Retaliation protection shields employees from adverse actions for reporting unlawful conduct.",
                "points": 1,
                "difficulty": "hard",
                "concept": "Retaliation Protection",
                "order_number": 1,
            },
            {
                "question_text": "Which condition is required to establish a hostile work environment?",
                "question_type": "multiple_choice",
                "options": [
                    "Conduct that is severe or pervasive enough to alter employment conditions",
                    "Any single minor verbal disagreement between colleagues",
                    "A written disagreement regarding standard work schedule hours",
                    "Disagreements that occur only outside of company working hours",
                ],
                "correct_answer": "Conduct that is severe or pervasive enough to alter employment conditions",
                "explanation": "Legal standards require conduct to be severe or pervasive.",
                "points": 1,
                "difficulty": "hard",
                "concept": "Hostile Work Environment",
                "order_number": 2,
            },
        ],
    }

    with patch("ai.quiz_generator.call_gemini_json", return_value=mock_gemini_response):
        res = client.post(
            f"/api/quizzes/generate/lesson/{lesson.id}",
            json={"num_questions": 2, "difficulty": "hard", "passing_score_percentage": 75},
        )

    assert res.status_code == 200, res.text
    data = res.json()

    assert data["title"] == f"Quiz: {lesson.title}"
    assert data["is_fallback"] is False
    assert len(data["questions"]) == 2
    assert data["passing_score_percentage"] == 75

    # Verify student response does NOT expose correct_answer or explanation
    for q in data["questions"]:
        assert "correct_answer" not in q
        assert "explanation" not in q
        assert len(q["options"]) == 4

    # Verify database persistence
    db_quiz = test_db.query(Quiz).filter(Quiz.lesson_id == lesson.id).first()
    assert db_quiz is not None
    assert db_quiz.is_fallback is False
    assert len(db_quiz.questions) == 2
    assert db_quiz.questions[0].correct_answer == "Protection against adverse employment action for reporting violations"


def test_fallback_generation_when_gemini_raises_llm_error(client, test_db):
    """Verifies that an LLMError triggers clean deterministic fallback with is_fallback=True."""
    lesson = seed_lesson_with_content(test_db)

    with patch("ai.quiz_generator.call_gemini_json", side_effect=LLMError("Network timeout calling Gemini")):
        res = client.post(
            f"/api/quizzes/generate/lesson/{lesson.id}",
            json={"num_questions": 3, "difficulty": "medium"},
        )

    assert res.status_code == 200, res.text
    data = res.json()

    assert data["is_fallback"] is True
    assert len(data["questions"]) == 3

    for q in data["questions"]:
        assert len(q["options"]) == 4
        assert "correct_answer" not in q
        assert "explanation" not in q

    # Check database persistence
    db_quiz = test_db.query(Quiz).filter(Quiz.lesson_id == lesson.id).first()
    assert db_quiz is not None
    assert db_quiz.is_fallback is True
    assert len(db_quiz.questions) == 3


def test_fallback_generation_when_gemini_quota_exhausted_429(client, test_db):
    """Verifies that HTTP 429 / RESOURCE_EXHAUSTED seamlessly activates the offline fallback."""
    lesson = seed_lesson_with_content(test_db)

    quota_error = LLMResponseError("Gemini API returned error code 429. Details: RESOURCE_EXHAUSTED quota exceeded.")
    with patch("ai.quiz_generator.call_gemini_json", side_effect=quota_error):
        res = client.post(
            f"/api/quizzes/generate/lesson/{lesson.id}",
            json={"num_questions": 4, "difficulty": "medium"},
        )

    assert res.status_code == 200
    data = res.json()
    assert data["is_fallback"] is True
    assert len(data["questions"]) == 4


def test_generate_quiz_lesson_not_found_404(client):
    """Verifies 404 when lesson does not exist."""
    res = client.post("/api/quizzes/generate/lesson/999999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_generate_quiz_missing_lesson_content_400(client, test_db):
    """Verifies 400 when lesson exists but has no educational content."""
    teacher = User(name="Teacher Empty", email="empty@test.com", role="teacher")
    test_db.add(teacher)
    test_db.commit()

    course = Course(title="Empty Course", teacher_id=teacher.id)
    test_db.add(course)
    test_db.commit()

    module = Module(course_id=course.id, title="Empty Module", order_number=1)
    test_db.add(module)
    test_db.commit()

    lesson = Lesson(module_id=module.id, title="Unprocessed Lesson", order_number=1)
    test_db.add(lesson)
    test_db.commit()

    res = client.post(f"/api/quizzes/generate/lesson/{lesson.id}")
    assert res.status_code == 400
    assert "no usable educational content" in res.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 4. Idempotency & Regeneration Tests
# ---------------------------------------------------------------------------

def test_quiz_regeneration_is_idempotent_and_prevents_duplicates(client, test_db):
    """
    CRITICAL IDEMPOTENCY REQUIREMENT:
    Repeated calls to generate quiz for a lesson must:
    - Update the quiz in place (preserve quiz.id)
    - Replace the old questions completely
    - Never create duplicate Quiz or orphan QuizQuestion records
    """
    lesson = seed_lesson_with_content(test_db)

    # Initial generation (5 questions)
    with patch("ai.quiz_generator.get_gemini_config", return_value=(None, "gemini-1.5-flash")):
        res1 = client.post(
            f"/api/quizzes/generate/lesson/{lesson.id}",
            json={"num_questions": 5},
        )
    assert res1.status_code == 200
    quiz_id_1 = res1.json()["id"]
    assert len(res1.json()["questions"]) == 5

    # Verify DB state after first run
    quizzes_count_1 = test_db.query(Quiz).filter(Quiz.lesson_id == lesson.id).count()
    questions_count_1 = test_db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id_1).count()
    assert quizzes_count_1 == 1
    assert questions_count_1 == 5

    # Second generation (regenerate with 3 questions)
    with patch("ai.quiz_generator.get_gemini_config", return_value=(None, "gemini-1.5-flash")):
        res2 = client.post(
            f"/api/quizzes/generate/lesson/{lesson.id}",
            json={"num_questions": 3, "difficulty": "easy"},
        )
    assert res2.status_code == 200
    quiz_id_2 = res2.json()["id"]
    assert len(res2.json()["questions"]) == 3

    # The Quiz ID must be preserved in-place
    assert quiz_id_2 == quiz_id_1

    # Verify DB state: NO duplicates or orphans
    quizzes_count_2 = test_db.query(Quiz).filter(Quiz.lesson_id == lesson.id).count()
    questions_count_2 = test_db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id_1).count()
    assert quizzes_count_2 == 1
    assert questions_count_2 == 3


# ---------------------------------------------------------------------------
# 5. Retrieval & Security Tests
# ---------------------------------------------------------------------------

def test_student_quiz_endpoints_do_not_leak_answers(client, test_db):
    """
    CRITICAL SECURITY TEST:
    Both GET /api/quizzes/lesson/{lesson_id} and GET /api/quizzes/{quiz_id}
    must NEVER leak correct_answer or explanation to students.
    """
    lesson = seed_lesson_with_content(test_db)

    # Generate quiz
    with patch("ai.quiz_generator.get_gemini_config", return_value=(None, "gemini-1.5-flash")):
        client.post(f"/api/quizzes/generate/lesson/{lesson.id}", json={"num_questions": 3})

    # Retrieve by lesson_id
    res_lesson = client.get(f"/api/quizzes/lesson/{lesson.id}")
    assert res_lesson.status_code == 200
    assert "correct_answer" not in res_lesson.text
    assert "explanation" not in res_lesson.text

    quiz_id = res_lesson.json()["id"]

    # Retrieve by quiz_id
    res_quiz = client.get(f"/api/quizzes/{quiz_id}")
    assert res_quiz.status_code == 200
    assert "correct_answer" not in res_quiz.text
    assert "explanation" not in res_quiz.text


def test_instructor_detail_endpoint_exposes_answers_and_explanations(client, test_db):
    """Verifies that instructor detail endpoint GET /api/quizzes/{quiz_id}/detail exposes answers."""
    lesson = seed_lesson_with_content(test_db)

    with patch("ai.quiz_generator.get_gemini_config", return_value=(None, "gemini-1.5-flash")):
        post_res = client.post(f"/api/quizzes/generate/lesson/{lesson.id}", json={"num_questions": 2})

    quiz_id = post_res.json()["id"]

    res_detail = client.get(f"/api/quizzes/{quiz_id}/detail")
    assert res_detail.status_code == 200
    data = res_detail.json()

    assert len(data["questions"]) == 2
    for q in data["questions"]:
        assert "correct_answer" in q
        assert "explanation" in q
        assert q["correct_answer"] in q["options"]
