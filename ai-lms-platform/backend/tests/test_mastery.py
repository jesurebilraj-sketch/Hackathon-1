"""
tests/test_mastery.py - Phase 5 Step 4 Tests: Concept Mastery Tracking & Weak-Topic Detection.

Covers:
1. All-correct quiz produces 100 mastery.
2. All-wrong quiz produces 0 mastery.
3. Partial concept score is calculated correctly.
4. Multiple questions of same concept aggregate correctly.
5. Different concepts create separate mastery records.
6. Concept normalization prevents duplicate records.
7. Status classification thresholds: "mastered" (>=80), "developing" (>=60), "weak" (<60).
8. Attempts count increments deterministically across submissions.
9. Weighted cumulative running average updates mastery across attempts.
10. Repeated quiz submissions update existing mastery in place without duplicating rows.
11. Lesson ID is preserved when quiz is lesson-scoped.
12. Weak topics endpoint returns only weak concepts sorted lowest score first.
13. Summary endpoint calculates total_concepts, mastered, developing, weak, and average_mastery accurately.
14. Nonexistent user returns 404.
15. Nonexistent course returns 404.
16. Mastery update failure rolls back QuizSubmission atomically.
17. Student mastery endpoints do not leak answers.
"""

import pytest
from unittest.mock import patch

from database.models import User, Course, Module, Lesson, Quiz, QuizQuestion, UserMastery, QuizSubmission
from ai.mastery import (
    classify_mastery_status,
    calculate_concept_performance,
    calculate_updated_mastery,
    MASTERY_THRESHOLD_MASTERED,
    MASTERY_THRESHOLD_DEVELOPING,
    STATUS_MASTERED,
    STATUS_DEVELOPING,
    STATUS_WEAK,
)
from tests.conftest import TestingSessionLocal


@pytest.fixture
def test_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_hierarchy_with_concepts(db) -> tuple:
    """Helper creating user, course, lesson, quiz, and questions with explicit concept tags."""
    teacher = User(name="Prof. Mastery", email="prof_mastery@test.com", role="teacher")
    student = User(name="Sam Student", email="sam_student@test.com", role="student")
    db.add_all([teacher, student])
    db.commit()
    db.refresh(teacher)
    db.refresh(student)

    course = Course(title="Data Structures", teacher_id=teacher.id)
    db.add(course)
    db.commit()
    db.refresh(course)

    module = Module(course_id=course.id, title="Trees", order_number=1)
    db.add(module)
    db.commit()
    db.refresh(module)

    lesson = Lesson(module_id=module.id, title="BST and AVL Trees", order_number=1)
    db.add(lesson)
    db.commit()
    db.refresh(lesson)

    quiz = Quiz(
        title="Tree Structures Checkpoint",
        course_id=course.id,
        module_id=module.id,
        lesson_id=lesson.id,
        passing_score_percentage=70,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    # Concept A: "Binary Search Tree" (2 questions, total 3 pts)
    q1 = QuizQuestion(
        quiz_id=quiz.id,
        question_text="What is a BST property?",
        options=["Left < Root < Right", "Left > Root > Right", "Random", "Heap order"],
        correct_answer="Left < Root < Right",
        explanation="BST requires left < root < right.",
        points=2,
        concept="Binary Search Tree",
        order_number=1,
    )
    q2 = QuizQuestion(
        quiz_id=quiz.id,
        question_text="Inorder traversal of a BST yields?",
        options=["Sorted order", "Reverse order", "Random order", "Level order"],
        correct_answer="Sorted order",
        explanation="Inorder traversal visits elements in ascending sorted order.",
        points=1,
        concept="Binary Search Tree",
        order_number=2,
    )

    # Concept B: "AVL Tree Balance" (1 question, 2 pts)
    q3 = QuizQuestion(
        quiz_id=quiz.id,
        question_text="What is the maximum allowed balance factor in an AVL tree?",
        options=["1", "2", "0", "3"],
        correct_answer="1",
        explanation="AVL balance factor must be -1, 0, or 1.",
        points=2,
        concept="AVL Tree Balance",
        order_number=3,
    )

    db.add_all([q1, q2, q3])
    db.commit()
    db.refresh(quiz)

    return quiz, [q1, q2, q3], student, course, lesson


# ---------------------------------------------------------------------------
# 1. Deterministic Calculation Unit Tests
# ---------------------------------------------------------------------------

def test_status_classification_boundaries():
    """Verifies that status thresholds are applied deterministically."""
    assert classify_mastery_status(100.0) == STATUS_MASTERED
    assert classify_mastery_status(80.0) == STATUS_MASTERED
    assert classify_mastery_status(79.99) == STATUS_DEVELOPING
    assert classify_mastery_status(60.0) == STATUS_DEVELOPING
    assert classify_mastery_status(59.99) == STATUS_WEAK
    assert classify_mastery_status(0.0) == STATUS_WEAK


def test_updated_mastery_running_average_formula():
    """
    Verifies cumulative weighted average formula:
    new_mastery = (prev_score * prev_attempts + current_score) / (prev_attempts + 1)
    """
    # First attempt: 100% -> 100.0, attempts=1
    score1, att1, stat1 = calculate_updated_mastery(None, 0, 100.0)
    assert score1 == 100.0
    assert att1 == 1
    assert stat1 == STATUS_MASTERED

    # Second attempt: 0% -> (100*1 + 0) / 2 = 50.0, attempts=2
    score2, att2, stat2 = calculate_updated_mastery(score1, att1, 0.0)
    assert score2 == 50.0
    assert att2 == 2
    assert stat2 == STATUS_WEAK

    # Third attempt: 80% -> (50*2 + 80) / 3 = 180 / 3 = 60.0, attempts=3
    score3, att3, stat3 = calculate_updated_mastery(score2, att2, 80.0)
    assert score3 == 60.0
    assert att3 == 3
    assert stat3 == STATUS_DEVELOPING


# ---------------------------------------------------------------------------
# 2. End-to-End Submission & Mastery Tracking Tests
# ---------------------------------------------------------------------------

def test_all_correct_quiz_produces_100_mastery(client, test_db):
    """Verifies that answering all questions for a concept produces 100.0 mastery and 'mastered' status."""
    quiz, questions, student, course, lesson = seed_hierarchy_with_concepts(test_db)
    q1, q2, q3 = questions

    # Submit all correct
    payload = {
        "user_id": student.id,
        "answers": {
            str(q1.id): "Left < Root < Right",
            str(q2.id): "Sorted order",
            str(q3.id): "1",
        },
    }

    res = client.post(f"/api/quizzes/{quiz.id}/submit", json=payload)
    assert res.status_code == 200

    # Verify UserMastery in database
    records = test_db.query(UserMastery).filter_by(user_id=student.id, course_id=course.id).all()
    assert len(records) == 2

    bst = next(r for r in records if r.concept == "Binary Search Tree")
    assert bst.mastery_score == 100.0
    assert bst.status == "mastered"
    assert bst.attempts_count == 1
    assert bst.lesson_id == lesson.id

    avl = next(r for r in records if r.concept == "AVL Tree Balance")
    assert avl.mastery_score == 100.0
    assert avl.status == "mastered"
    assert avl.attempts_count == 1


def test_all_wrong_quiz_produces_0_mastery(client, test_db):
    """Verifies that answering all questions wrong produces 0.0 mastery and 'weak' status."""
    quiz, questions, student, course, _ = seed_hierarchy_with_concepts(test_db)
    q1, q2, q3 = questions

    # Submit all wrong
    payload = {
        "user_id": student.id,
        "answers": {
            str(q1.id): "Random",
            str(q2.id): "Random order",
            str(q3.id): "0",
        },
    }

    res = client.post(f"/api/quizzes/{quiz.id}/submit", json=payload)
    assert res.status_code == 200

    records = test_db.query(UserMastery).filter_by(user_id=student.id, course_id=course.id).all()
    assert len(records) == 2
    for r in records:
        assert r.mastery_score == 0.0
        assert r.status == "weak"
        assert r.attempts_count == 1


def test_partial_concept_score_and_weighting(client, test_db):
    """
    Q1 (2 pts, correct) + Q2 (1 pt, wrong) for 'Binary Search Tree'.
    Earned = 2, Possible = 3 -> 2/3 * 100 = 66.67%. Status = 'developing'.
    """
    quiz, questions, student, course, _ = seed_hierarchy_with_concepts(test_db)
    q1, q2, q3 = questions

    payload = {
        "user_id": student.id,
        "answers": {
            str(q1.id): "Left < Root < Right",  # +2 pts
            str(q2.id): "Random order",         # 0 pts
            str(q3.id): "0",                    # wrong (AVL)
        },
    }

    res = client.post(f"/api/quizzes/{quiz.id}/submit", json=payload)
    assert res.status_code == 200

    bst = test_db.query(UserMastery).filter_by(user_id=student.id, concept="Binary Search Tree").first()
    assert bst is not None
    assert bst.mastery_score == 66.67
    assert bst.status == "developing"


def test_multiple_questions_same_concept_aggregate_correctly(client, test_db):
    """
    Verifies that multiple questions with the exact same concept aggregate points:
    Q1: 2 pts, correct
    Q2: 1 pt, incorrect
    Q3: 2 pts, correct
    Total earned = 4, Total possible = 5 -> mastery_score = 80.0, status = 'mastered'
    """
    quiz, _, student, course, lesson = seed_hierarchy_with_concepts(test_db)
    quiz_agg = Quiz(title="Aggregation Quiz", course_id=course.id, lesson_id=lesson.id)
    test_db.add(quiz_agg)
    test_db.commit()

    q1 = QuizQuestion(
        quiz_id=quiz_agg.id,
        question_text="Q1",
        options=["A", "B", "C", "D"],
        correct_answer="A",
        explanation="Exp",
        points=2,
        concept="Concept Aggregation Test",
        order_number=1,
    )
    q2 = QuizQuestion(
        quiz_id=quiz_agg.id,
        question_text="Q2",
        options=["A", "B", "C", "D"],
        correct_answer="A",
        explanation="Exp",
        points=1,
        concept="Concept Aggregation Test",
        order_number=2,
    )
    q3 = QuizQuestion(
        quiz_id=quiz_agg.id,
        question_text="Q3",
        options=["A", "B", "C", "D"],
        correct_answer="A",
        explanation="Exp",
        points=2,
        concept="Concept Aggregation Test",
        order_number=3,
    )
    test_db.add_all([q1, q2, q3])
    test_db.commit()

    # Q1 correct (+2), Q2 wrong (0), Q3 correct (+2) -> 4/5 = 80.0
    payload = {
        "user_id": student.id,
        "answers": {str(q1.id): "A", str(q2.id): "B", str(q3.id): "A"},
    }
    res = client.post(f"/api/quizzes/{quiz_agg.id}/submit", json=payload)
    assert res.status_code == 200

    rec = test_db.query(UserMastery).filter_by(
        user_id=student.id,
        concept="Concept Aggregation Test",
    ).first()
    assert rec is not None
    assert rec.mastery_score == 80.0
    assert rec.status == "mastered"
    assert rec.attempts_count == 1


def test_concept_normalization_prevents_duplicate_records(client, test_db):
    """
    Verifies that concepts differing only by whitespace/casing map to the same
    logical concept record without creating duplicates.
    """
    _, _, student, course, lesson = seed_hierarchy_with_concepts(test_db)

    quiz2 = Quiz(title="Normalization Quiz", course_id=course.id, lesson_id=lesson.id)
    test_db.add(quiz2)
    test_db.commit()

    q_a = QuizQuestion(
        quiz_id=quiz2.id,
        question_text="Q A",
        options=["1", "2", "3", "4"],
        correct_answer="1",
        explanation="Exp",
        points=1,
        concept="Hash Tables",  # Normal
        order_number=1,
    )
    q_b = QuizQuestion(
        quiz_id=quiz2.id,
        question_text="Q B",
        options=["1", "2", "3", "4"],
        correct_answer="1",
        explanation="Exp",
        points=1,
        concept=" hash tables ",  # Leading/trailing whitespace + lowercase
        order_number=2,
    )
    q_c = QuizQuestion(
        quiz_id=quiz2.id,
        question_text="Q C",
        options=["1", "2", "3", "4"],
        correct_answer="1",
        explanation="Exp",
        points=1,
        concept="HASH TABLES",  # Uppercase
        order_number=3,
    )
    test_db.add_all([q_a, q_b, q_c])
    test_db.commit()

    # Submit all correct
    payload = {
        "user_id": student.id,
        "answers": {str(q_a.id): "1", str(q_b.id): "1", str(q_c.id): "1"},
    }

    res = client.post(f"/api/quizzes/{quiz2.id}/submit", json=payload)
    assert res.status_code == 200

    # Verify only 1 record exists in DB for this concept
    records = test_db.query(UserMastery).filter(
        UserMastery.user_id == student.id,
        UserMastery.course_id == course.id,
        UserMastery.concept.ilike("%hash tables%"),
    ).all()

    assert len(records) == 1
    assert records[0].mastery_score == 100.0


def test_repeated_submissions_update_existing_mastery_in_place(client, test_db):
    """
    Verifies that repeated quiz submissions update existing rows in place
    and increment attempts_count without duplicating rows.
    """
    quiz, questions, student, course, _ = seed_hierarchy_with_concepts(test_db)
    q1 = questions[0]

    # Attempt 1: correct (100%)
    client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"user_id": student.id, "answers": {str(q1.id): "Left < Root < Right"}},
    )
    rec1 = test_db.query(UserMastery).filter_by(user_id=student.id, concept="Binary Search Tree").first()
    assert rec1.attempts_count == 1
    rec_id = rec1.id

    # Attempt 2: wrong (0%)
    client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"user_id": student.id, "answers": {str(q1.id): "Random"}},
    )
    test_db.expire_all()
    rec2 = test_db.query(UserMastery).filter_by(user_id=student.id, concept="Binary Search Tree").all()
    # Still exactly ONE row in database
    assert len(rec2) == 1
    assert rec2[0].id == rec_id
    assert rec2[0].attempts_count == 2
    # Score updated according to running average
    assert rec2[0].mastery_score < 100.0


# ---------------------------------------------------------------------------
# 3. Mastery API Endpoints Tests
# ---------------------------------------------------------------------------

def test_get_user_course_mastery_endpoint(client, test_db):
    """Verifies GET /api/mastery/user/{user_id}/course/{course_id} returns all concept records."""
    quiz, questions, student, course, _ = seed_hierarchy_with_concepts(test_db)
    q1, _, q3 = questions

    # Submit answers
    client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"user_id": student.id, "answers": {str(q1.id): "Left < Root < Right", str(q3.id): "1"}},
    )

    res = client.get(f"/api/mastery/user/{student.id}/course/{course.id}")
    assert res.status_code == 200
    data = res.json()

    assert len(data) == 2
    concept_names = [d["concept"] for d in data]
    assert "Binary Search Tree" in concept_names
    assert "AVL Tree Balance" in concept_names


def test_get_weak_topics_endpoint_filters_and_sorts_lowest_first(client, test_db):
    """
    Verifies GET /api/mastery/user/{user_id}/course/{course_id}/weak:
    - Excludes concepts with score >= 60.
    - Sorts weak concepts lowest score first.
    """
    _, _, student, course, _ = seed_hierarchy_with_concepts(test_db)

    # Seed 3 manual UserMastery records
    m1 = UserMastery(user_id=student.id, course_id=course.id, concept="Concept Weak 1", mastery_score=40.0, status="weak")
    m2 = UserMastery(user_id=student.id, course_id=course.id, concept="Concept Weak 2", mastery_score=20.0, status="weak")
    m3 = UserMastery(user_id=student.id, course_id=course.id, concept="Concept Mastered", mastery_score=85.0, status="mastered")
    m4 = UserMastery(user_id=student.id, course_id=course.id, concept="Concept Developing", mastery_score=65.0, status="developing")
    test_db.add_all([m1, m2, m3, m4])
    test_db.commit()

    res = client.get(f"/api/mastery/user/{student.id}/course/{course.id}/weak")
    assert res.status_code == 200
    weak_data = res.json()

    assert len(weak_data) == 2
    # Lowest score first: 20.0 then 40.0
    assert weak_data[0]["concept"] == "Concept Weak 2"
    assert weak_data[0]["mastery_score"] == 20.0
    assert weak_data[1]["concept"] == "Concept Weak 1"
    assert weak_data[1]["mastery_score"] == 40.0


def test_get_course_mastery_summary_endpoint(client, test_db):
    """
    Verifies GET /api/mastery/user/{user_id}/course/{course_id}/summary returns accurate:
    - total_concepts
    - mastered count
    - developing count
    - weak count
    - average_mastery
    - weak_concepts list
    """
    _, _, student, course, _ = seed_hierarchy_with_concepts(test_db)

    m1 = UserMastery(user_id=student.id, course_id=course.id, concept="T1", mastery_score=90.0, status="mastered")
    m2 = UserMastery(user_id=student.id, course_id=course.id, concept="T2", mastery_score=80.0, status="mastered")
    m3 = UserMastery(user_id=student.id, course_id=course.id, concept="T3", mastery_score=70.0, status="developing")
    m4 = UserMastery(user_id=student.id, course_id=course.id, concept="T4", mastery_score=40.0, status="weak")
    # Total = 4 concepts. Sum = 90 + 80 + 70 + 40 = 280. Avg = 70.0.
    test_db.add_all([m1, m2, m3, m4])
    test_db.commit()

    res = client.get(f"/api/mastery/user/{student.id}/course/{course.id}/summary")
    assert res.status_code == 200
    summary = res.json()

    assert summary["user_id"] == student.id
    assert summary["course_id"] == course.id
    assert summary["total_concepts"] == 4
    assert summary["mastered"] == 2
    assert summary["developing"] == 1
    assert summary["weak"] == 1
    assert summary["average_mastery"] == 70.0
    assert len(summary["weak_concepts"]) == 1
    assert summary["weak_concepts"][0]["concept"] == "T4"


def test_mastery_endpoints_404_for_nonexistent_user_or_course(client, test_db):
    """Verifies that all mastery endpoints return 404 for nonexistent user or course."""
    _, _, student, course, _ = seed_hierarchy_with_concepts(test_db)

    # Nonexistent user
    res1 = client.get(f"/api/mastery/user/999999/course/{course.id}")
    assert res1.status_code == 404
    assert "user with id 999999 not found" in res1.json()["detail"].lower()

    # Nonexistent course
    res2 = client.get(f"/api/mastery/user/{student.id}/course/999999")
    assert res2.status_code == 404
    assert "course with id 999999 not found" in res2.json()["detail"].lower()

    # Weak endpoint nonexistent user
    res3 = client.get(f"/api/mastery/user/999999/course/{course.id}/weak")
    assert res3.status_code == 404

    # Summary endpoint nonexistent course
    res4 = client.get(f"/api/mastery/user/{student.id}/course/999999/summary")
    assert res4.status_code == 404


# ---------------------------------------------------------------------------
# 4. Transaction Safety & Security Tests
# ---------------------------------------------------------------------------

def test_mastery_update_failure_rolls_back_quiz_submission(client, test_db):
    """
    CRITICAL TRANSACTION SAFETY TEST:
    If mastery calculation / record updating raises an exception,
    the entire transaction must roll back so that NO QuizSubmission
    is persisted without its corresponding mastery updates.
    """
    quiz, questions, student, _, _ = seed_hierarchy_with_concepts(test_db)
    q1 = questions[0]

    payload = {
        "user_id": student.id,
        "answers": {str(q1.id): "Left < Root < Right"},
    }

    with patch(
        "api.quizzes.update_user_mastery_for_submission",
        side_effect=RuntimeError("Simulated Mastery Service Crash"),
    ):
        res = client.post(f"/api/quizzes/{quiz.id}/submit", json=payload)

    assert res.status_code == 500
    assert "database error" in res.json()["detail"].lower()

    # Verify atomic rollback: NO QuizSubmission or UserMastery was persisted
    assert test_db.query(QuizSubmission).filter_by(quiz_id=quiz.id).count() == 0
    assert test_db.query(UserMastery).filter_by(user_id=student.id).count() == 0


def test_student_mastery_endpoints_do_not_leak_answers(client, test_db):
    """
    SECURITY TEST:
    Verifies that student-facing mastery responses NEVER expose correct_answer or explanation.
    """
    quiz, questions, student, course, _ = seed_hierarchy_with_concepts(test_db)
    q1 = questions[0]

    client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"user_id": student.id, "answers": {str(q1.id): "Left < Root < Right"}},
    )

    res = client.get(f"/api/mastery/user/{student.id}/course/{course.id}")
    assert res.status_code == 200
    assert "correct_answer" not in res.text
    assert "explanation" not in res.text
