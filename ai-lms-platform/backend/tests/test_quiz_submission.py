"""
tests/test_quiz_submission.py - Phase 5 Step 3 Tests: Quiz Submission, Automatic Grading & Feedback.

Covers:
1. Successful all-correct submission.
2. Successful partially-correct submission.
3. Zero-score submission.
4. Correct percentage calculation.
5. Correct passing/failing behavior according to quiz.passing_score_percentage.
6. Points-based grading with varied question point weights.
7. Explicit missing answers handling (awarded 0 points without errors).
8. Unknown question ID rejection (400).
9. Invalid option rejection (not among 4 options, 400).
10. Quiz-not-found behavior (404).
11. User-not-found behavior (404).
12. Database persistence of QuizSubmission record.
13. Per-question feedback breakdown with explanations and concept tags.
14. Submission history retrieval with user_id filtering.
15. Student quiz retrieval endpoints still conceal answers and explanations.
16. Zero-questions quiz edge case rejection (400).
17. Database error transaction rollback.
"""

import pytest
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError

from database.models import User, Course, Module, Lesson, Quiz, QuizQuestion, QuizSubmission
from tests.conftest import TestingSessionLocal


@pytest.fixture
def test_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_quiz_with_questions(db, passing_score=70) -> tuple:
    """Helper creating teacher, student, course, lesson, quiz, and 3 weighted questions."""
    teacher = User(name="Prof. Quiz", email="prof_quiz@example.com", role="teacher")
    student1 = User(name="Alice Learner", email="alice_learner@example.com", role="student")
    student2 = User(name="Bob Learner", email="bob_learner@example.com", role="student")
    db.add_all([teacher, student1, student2])
    db.commit()
    db.refresh(teacher)
    db.refresh(student1)
    db.refresh(student2)

    course = Course(title="Algorithms 101", teacher_id=teacher.id)
    db.add(course)
    db.commit()
    db.refresh(course)

    module = Module(course_id=course.id, title="Module 1", order_number=1)
    db.add(module)
    db.commit()
    db.refresh(module)

    lesson = Lesson(
        module_id=module.id,
        title="Binary Search",
        content="Binary search requires sorted arrays and operates in O(log n) time.",
        order_number=1,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)

    quiz = Quiz(
        title="Binary Search Mastery Check",
        description="Test your understanding of logarithmic search algorithms",
        course_id=course.id,
        module_id=module.id,
        lesson_id=lesson.id,
        quiz_type="lesson_quiz",
        passing_score_percentage=passing_score,
        time_limit_minutes=15,
        is_fallback=False,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    q1 = QuizQuestion(
        quiz_id=quiz.id,
        question_text="What is the prerequisite for binary search?",
        question_type="multiple_choice",
        options=["Array must be sorted", "Array must be empty", "Array must contain only integers", "Array size must be prime"],
        correct_answer="Array must be sorted",
        explanation="Binary search requires the underlying array to be pre-sorted.",
        points=1,
        difficulty="easy",
        concept="Prerequisites",
        order_number=1,
    )
    q2 = QuizQuestion(
        quiz_id=quiz.id,
        question_text="What is the average time complexity of binary search?",
        question_type="multiple_choice",
        options=["O(1)", "O(log n)", "O(n)", "O(n^2)"],
        correct_answer="O(log n)",
        explanation="The search space is halved in each step yielding O(log n) complexity.",
        points=2,
        difficulty="medium",
        concept="Time Complexity",
        order_number=2,
    )
    q3 = QuizQuestion(
        quiz_id=quiz.id,
        question_text="What is returned when the target element is not found?",
        question_type="multiple_choice",
        options=["-1", "0", "None of these", "Infinity"],
        correct_answer="-1",
        explanation="Standard convention returns -1 or not found indicator.",
        points=3,
        difficulty="hard",
        concept="Sentinel Return",
        order_number=3,
    )
    db.add_all([q1, q2, q3])
    db.commit()
    db.refresh(quiz)

    return quiz, [q1, q2, q3], student1, student2


# ---------------------------------------------------------------------------
# 1. Successful Grading Tests
# ---------------------------------------------------------------------------

def test_successful_all_correct_submission(client, test_db):
    """Verifies that an all-correct submission earns 100%, full points, and passed=True."""
    quiz, questions, student, _ = seed_quiz_with_questions(test_db, passing_score=70)
    q1, q2, q3 = questions

    payload = {
        "user_id": student.id,
        "answers": {
            str(q1.id): "Array must be sorted",
            str(q2.id): "O(log n)",
            str(q3.id): "-1",
        },
    }

    res = client.post(f"/api/quizzes/{quiz.id}/submit", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["quiz_id"] == quiz.id
    assert data["user_id"] == student.id
    assert data["score"] == 6.0  # 1 + 2 + 3
    assert data["max_score"] == 6.0
    assert data["percentage"] == 100.0
    assert data["passed"] is True
    assert len(data["feedback"]) == 3

    for fb in data["feedback"]:
        assert fb["is_correct"] is True
        assert fb["points_earned"] == fb["points_possible"]
        assert fb["correct_answer"] is not None
        assert fb["explanation"] is not None
        assert fb["concept"] is not None


def test_successful_partially_correct_submission(client, test_db):
    """Verifies partial credit scoring and passed flag based on passing_score_percentage."""
    # Total points: 6. Q1(1pt, correct) + Q2(2pts, correct) + Q3(3pts, wrong) = 3pts = 50%
    # With passing_score=70, passed must be False
    quiz, questions, student, _ = seed_quiz_with_questions(test_db, passing_score=70)
    q1, q2, q3 = questions

    payload = {
        "user_id": student.id,
        "answers": {
            str(q1.id): "Array must be sorted",  # correct (+1)
            str(q2.id): "O(log n)",               # correct (+2)
            str(q3.id): "0",                      # wrong (0)
        },
    }

    res = client.post(f"/api/quizzes/{quiz.id}/submit", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["score"] == 3.0
    assert data["max_score"] == 6.0
    assert data["percentage"] == 50.0
    assert data["passed"] is False

    fb_map = {f["question_id"]: f for f in data["feedback"]}
    assert fb_map[q1.id]["is_correct"] is True
    assert fb_map[q1.id]["points_earned"] == 1.0
    assert fb_map[q2.id]["is_correct"] is True
    assert fb_map[q2.id]["points_earned"] == 2.0
    assert fb_map[q3.id]["is_correct"] is False
    assert fb_map[q3.id]["points_earned"] == 0.0
    assert fb_map[q3.id]["user_answer"] == "0"
    assert fb_map[q3.id]["correct_answer"] == "-1"


def test_zero_score_submission(client, test_db):
    """Verifies zero score when all answers are incorrect."""
    quiz, questions, student, _ = seed_quiz_with_questions(test_db, passing_score=70)
    q1, q2, q3 = questions

    payload = {
        "user_id": student.id,
        "answers": {
            str(q1.id): "Array must be empty",
            str(q2.id): "O(n)",
            str(q3.id): "Infinity",
        },
    }

    res = client.post(f"/api/quizzes/{quiz.id}/submit", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["score"] == 0.0
    assert data["max_score"] == 6.0
    assert data["percentage"] == 0.0
    assert data["passed"] is False


def test_passing_threshold_exact_boundary(client, test_db):
    """Verifies passing status when score exactly meets passing_score_percentage."""
    # Q1(1) + Q2(2) = 3 / 6 = 50%. Setting passing_score=50 -> passed must be True.
    quiz, questions, student, _ = seed_quiz_with_questions(test_db, passing_score=50)
    q1, q2, q3 = questions

    payload = {
        "user_id": student.id,
        "answers": {
            str(q1.id): "Array must be sorted",  # +1
            str(q2.id): "O(log n)",               # +2
            str(q3.id): "Infinity",               # 0
        },
    }

    res = client.post(f"/api/quizzes/{quiz.id}/submit", json=payload)
    assert res.status_code == 200
    assert res.json()["percentage"] == 50.0
    assert res.json()["passed"] is True


def test_missing_answers_handled_gracefully(client, test_db):
    """
    Verifies that omitting answers for some questions awards 0 points for the omitted
    questions without causing any errors or misleading scores.
    """
    quiz, questions, student, _ = seed_quiz_with_questions(test_db, passing_score=70)
    q1, q2, q3 = questions

    # Only answer Q1; leave Q2 and Q3 completely omitted
    payload = {
        "user_id": student.id,
        "answers": {
            str(q1.id): "Array must be sorted",
        },
    }

    res = client.post(f"/api/quizzes/{quiz.id}/submit", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["score"] == 1.0
    assert data["max_score"] == 6.0
    assert data["percentage"] == 16.67
    assert data["passed"] is False

    fb_map = {f["question_id"]: f for f in data["feedback"]}
    assert fb_map[q1.id]["is_correct"] is True
    assert fb_map[q2.id]["is_correct"] is False
    assert fb_map[q2.id]["user_answer"] is None
    assert fb_map[q3.id]["is_correct"] is False
    assert fb_map[q3.id]["user_answer"] is None


# ---------------------------------------------------------------------------
# 2. Input Validation & Error Handling Tests
# ---------------------------------------------------------------------------

def test_reject_unknown_question_id_400(client, test_db):
    """Verifies 400 Bad Request when an answer references an unknown question ID."""
    quiz, _, student, _ = seed_quiz_with_questions(test_db)

    payload = {
        "user_id": student.id,
        "answers": {
            "999999": "Some Option",
        },
    }

    res = client.post(f"/api/quizzes/{quiz.id}/submit", json=payload)
    assert res.status_code == 400
    assert "invalid question id" in res.json()["detail"].lower()


def test_reject_invalid_option_choice_400(client, test_db):
    """Verifies 400 Bad Request when submitted option is not among the question's 4 choices."""
    quiz, questions, student, _ = seed_quiz_with_questions(test_db)
    q1 = questions[0]

    payload = {
        "user_id": student.id,
        "answers": {
            str(q1.id): "Completely Nonexistent Option",
        },
    }

    res = client.post(f"/api/quizzes/{quiz.id}/submit", json=payload)
    assert res.status_code == 400
    assert "invalid option" in res.json()["detail"].lower()


def test_submit_quiz_not_found_404(client, test_db):
    """Verifies 404 when quiz does not exist."""
    _, _, student, _ = seed_quiz_with_questions(test_db)

    payload = {"user_id": student.id, "answers": {}}
    res = client.post("/api/quizzes/999999/submit", json=payload)
    assert res.status_code == 404
    assert "quiz with id 999999 not found" in res.json()["detail"].lower()


def test_submit_user_not_found_404(client, test_db):
    """Verifies 404 when student user does not exist."""
    quiz, _, _, _ = seed_quiz_with_questions(test_db)

    payload = {"user_id": 999999, "answers": {}}
    res = client.post(f"/api/quizzes/{quiz.id}/submit", json=payload)
    assert res.status_code == 404
    assert "user with id 999999 not found" in res.json()["detail"].lower()


def test_empty_quiz_with_no_questions_rejected_400(client, test_db):
    """Verifies 400 when attempting to grade an empty quiz."""
    teacher = User(name="Teacher", email="t_empty_q@example.com", role="teacher")
    student = User(name="Student", email="s_empty_q@example.com", role="student")
    test_db.add_all([teacher, student])
    test_db.commit()

    course = Course(title="Course", teacher_id=teacher.id)
    test_db.add(course)
    test_db.commit()

    empty_quiz = Quiz(title="Empty Quiz", course_id=course.id)
    test_db.add(empty_quiz)
    test_db.commit()

    payload = {"user_id": student.id, "answers": {}}
    res = client.post(f"/api/quizzes/{empty_quiz.id}/submit", json=payload)
    assert res.status_code == 400
    assert "no questions" in res.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 3. Database Persistence & History Tests
# ---------------------------------------------------------------------------

def test_submission_persisted_in_database(client, test_db):
    """Verifies that QuizSubmission row is accurately persisted in the database."""
    quiz, questions, student, _ = seed_quiz_with_questions(test_db)
    q1, q2, q3 = questions

    payload = {
        "user_id": student.id,
        "answers": {
            str(q1.id): "Array must be sorted",
            str(q2.id): "O(log n)",
            str(q3.id): "-1",
        },
    }

    res = client.post(f"/api/quizzes/{quiz.id}/submit", json=payload)
    assert res.status_code == 200
    sub_id = res.json()["id"]

    db_sub = test_db.query(QuizSubmission).filter(QuizSubmission.id == sub_id).first()
    assert db_sub is not None
    assert db_sub.quiz_id == quiz.id
    assert db_sub.user_id == student.id
    assert db_sub.score == 6.0
    assert db_sub.percentage == 100.0
    assert db_sub.passed is True
    assert db_sub.answers[str(q1.id)] == "Array must be sorted"
    assert len(db_sub.feedback) == 3


def test_submission_history_with_user_id_filtering(client, test_db):
    """Verifies GET /api/quizzes/{quiz_id}/submissions and user_id filtering isolation."""
    quiz, questions, student1, student2 = seed_quiz_with_questions(test_db)
    q1 = questions[0]

    # Student 1 submits twice
    client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"user_id": student1.id, "answers": {str(q1.id): "Array must be sorted"}},
    )
    client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"user_id": student1.id, "answers": {str(q1.id): "Array must be empty"}},
    )

    # Student 2 submits once
    client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"user_id": student2.id, "answers": {str(q1.id): "Array must be sorted"}},
    )

    # 1. Total submissions for quiz = 3
    res_all = client.get(f"/api/quizzes/{quiz.id}/submissions")
    assert res_all.status_code == 200
    assert len(res_all.json()) == 3

    # 2. Filter by student 1 -> only 2 submissions
    res_s1 = client.get(f"/api/quizzes/{quiz.id}/submissions?user_id={student1.id}")
    assert res_s1.status_code == 200
    assert len(res_s1.json()) == 2
    for item in res_s1.json():
        assert item["user_id"] == student1.id

    # 3. Filter by student 2 -> only 1 submission
    res_s2 = client.get(f"/api/quizzes/{quiz.id}/submissions?user_id={student2.id}")
    assert res_s2.status_code == 200
    assert len(res_s2.json()) == 1
    assert res_s2.json()[0]["user_id"] == student2.id


def test_student_quiz_endpoints_still_conceal_answers_after_submission(client, test_db):
    """
    CRITICAL SECURITY TEST:
    Even after a submission has been processed and answers revealed on the result payload,
    GET /api/quizzes/{quiz_id} and GET /api/quizzes/lesson/{lesson_id}
    MUST NEVER leak correct answers or explanations.
    """
    quiz, questions, student, _ = seed_quiz_with_questions(test_db)
    q1 = questions[0]

    # Submit quiz
    client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"user_id": student.id, "answers": {str(q1.id): "Array must be sorted"}},
    )

    # Check student quiz endpoint
    res = client.get(f"/api/quizzes/{quiz.id}")
    assert res.status_code == 200
    assert "correct_answer" not in res.text
    assert "explanation" not in res.text


def test_database_error_rolls_back_submission(client, test_db):
    """Verifies transaction rollback on database commit failure during submission."""
    quiz, questions, student, _ = seed_quiz_with_questions(test_db)
    q1 = questions[0]

    payload = {
        "user_id": student.id,
        "answers": {str(q1.id): "Array must be sorted"},
    }

    with patch("sqlalchemy.orm.Session.commit", side_effect=SQLAlchemyError("Simulated DB Disk Full")):
        res = client.post(f"/api/quizzes/{quiz.id}/submit", json=payload)

    assert res.status_code == 500
    assert "database error" in res.json()["detail"].lower()

    # Ensure no partial submission row was committed
    assert test_db.query(QuizSubmission).filter(QuizSubmission.quiz_id == quiz.id).count() == 0


def test_points_based_grading_different_weights(client, test_db):
    """Verifies that questions with different point values contribute proportionately."""
    quiz, questions, student, _ = seed_quiz_with_questions(test_db)
    q1, q2, q3 = questions  # q1=1pt, q2=2pts, q3=3pts -> total=6pts

    # Answer Q1 wrong (0/1), Q2 correct (2/2), Q3 correct (3/3) -> score = 5.0/6.0 = 83.33%
    payload = {
        "user_id": student.id,
        "answers": {
            str(q1.id): "Array must be empty",  # wrong
            str(q2.id): "O(log n)",             # correct (+2)
            str(q3.id): "-1",                   # correct (+3)
        },
    }

    res = client.post(f"/api/quizzes/{quiz.id}/submit", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["score"] == 5.0
    assert data["max_score"] == 6.0
    assert data["percentage"] == 83.33
    assert data["passed"] is True


def test_client_cannot_tamper_with_score_or_passed(client, test_db):
    """Verifies that server-side grading completely ignores client-supplied score or passed fields."""
    quiz, questions, student, _ = seed_quiz_with_questions(test_db)
    q1 = questions[0]

    # Malicious client attempting to inject score=100.0 and passed=True while submitting wrong answer
    payload = {
        "user_id": student.id,
        "answers": {str(q1.id): "Array must be empty"},  # wrong answer
        "score": 100.0,
        "percentage": 100.0,
        "passed": True,
    }

    res = client.post(f"/api/quizzes/{quiz.id}/submit", json=payload)
    assert res.status_code == 200
    data = res.json()
    # Injected values MUST be ignored; calculated score is 0.0, passed is False
    assert data["score"] == 0.0
    assert data["percentage"] == 0.0
    assert data["passed"] is False

