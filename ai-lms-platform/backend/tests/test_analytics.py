"""
tests/test_analytics.py - Phase 8 Tests: Student Course Analytics & Dashboard Intelligence.

Covers:
1. Successful analytics response (/api/analytics/user/{user_id}/course/{course_id}).
2. Correct lesson progress calculation (total, completed, percentage).
3. Quiz performance calculation (attempted, average, best, passed, pass rate).
4. Mastery calculation (total, mastered, developing, weak counts, average, weak topics).
5. Study activity calculation (planned minutes, completed minutes, completed/missed/scheduled sessions).
6. User/course 404 handling.
7. Empty/no-activity case (safe zero/empty response).
8. Strict user and course isolation (no data leakage across users or courses).
9. Security/zero answer leakage: Performance history endpoints never expose quiz answer keys or explanations.
10. Dashboard overview endpoint (/api/analytics/user/{user_id}/course/{course_id}/overview).
11. Analytics service status endpoint (/api/analytics/).
"""

from datetime import date, datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from database.models import (
    User,
    Course,
    Module,
    Lesson,
    Quiz,
    QuizQuestion,
    QuizSubmission,
    UserMastery,
    StudyPlan,
    StudySession,
)
from tests.conftest import TestingSessionLocal


@pytest.fixture
def test_db():
    """Provides a fresh isolated database session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_analytics_data(db) -> dict:
    """
    Seeds a realistic multi-user, multi-course dataset for analytics verification.
    """
    # 1. Users
    teacher = User(name="Prof. Analytics", email="prof_analytics@example.com", role="teacher")
    student1 = User(name="Alice Student", email="alice_analytics@example.com", role="student")
    student2 = User(name="Bob Student", email="bob_analytics@example.com", role="student")
    db.add_all([teacher, student1, student2])
    db.commit()

    # 2. Courses
    course1 = Course(title="Computer Science 101", teacher_id=teacher.id)
    course2 = Course(title="Biology 202", teacher_id=teacher.id)
    db.add_all([course1, course2])
    db.commit()

    # 3. Course 1 Structure: 1 module with 3 lessons
    m1 = Module(course_id=course1.id, title="Module 1: Foundations", order_number=1)
    db.add(m1)
    db.commit()

    l1 = Lesson(module_id=m1.id, title="Lesson 1: Binary Trees", order_number=1, estimated_minutes=30)
    l2 = Lesson(module_id=m1.id, title="Lesson 2: Graph Theory", order_number=2, estimated_minutes=45)
    l3 = Lesson(module_id=m1.id, title="Lesson 3: Dynamic Programming", order_number=3, estimated_minutes=60)
    db.add_all([l1, l2, l3])
    db.commit()

    # 4. Course 1 Quizzes: 2 quizzes
    q1 = Quiz(title="Binary Trees Quiz", course_id=course1.id, module_id=m1.id, lesson_id=l1.id, passing_score_percentage=70)
    q2 = Quiz(title="Graph Theory Quiz", course_id=course1.id, module_id=m1.id, lesson_id=l2.id, passing_score_percentage=70)
    db.add_all([q1, q2])
    db.commit()

    # Add questions with answers to verify zero-leakage
    qq1 = QuizQuestion(
        quiz_id=q1.id,
        question_text="What is a tree?",
        options=["Option A", "Option B", "Option C", "Option D"],
        correct_answer="Option A",
        explanation="Secret teacher explanation 1",
        points=2,
    )
    qq2 = QuizQuestion(
        quiz_id=q2.id,
        question_text="What is a graph?",
        options=["Option A", "Option B", "Option C", "Option D"],
        correct_answer="Option B",
        explanation="Secret teacher explanation 2",
        points=2,
    )
    db.add_all([qq1, qq2])
    db.commit()

    # 5. Student 1 Submissions in Course 1:
    # Quiz 1: score=2/2, 100%, passed
    sub1 = QuizSubmission(
        quiz_id=q1.id,
        user_id=student1.id,
        score=2.0,
        max_score=2.0,
        percentage=100.0,
        passed=True,
        answers={"1": "Option A"},
        feedback={"1": {"correct": True, "explanation": "Secret teacher explanation 1"}},
        submitted_at=datetime.utcnow() - timedelta(days=2),
    )
    # Quiz 2: score=1/2, 50%, failed
    sub2 = QuizSubmission(
        quiz_id=q2.id,
        user_id=student1.id,
        score=1.0,
        max_score=2.0,
        percentage=50.0,
        passed=False,
        answers={"2": "Option C"},
        feedback={"2": {"correct": False, "explanation": "Secret teacher explanation 2"}},
        submitted_at=datetime.utcnow() - timedelta(days=1),
    )
    db.add_all([sub1, sub2])
    db.commit()

    # 6. Student 1 Study Plan & Sessions in Course 1:
    # 4 sessions:
    # - session 1 (lesson 1): 40 min, completed
    # - session 2 (lesson 2): 50 min, completed
    # - session 3 (lesson 3): 60 min, scheduled
    # - session 4 (lesson 1 revision): 30 min, missed
    plan1 = StudyPlan(
        user_id=student1.id,
        course_id=course1.id,
        exam_date=date.today() + timedelta(days=14),
        total_planned_minutes=180,
    )
    db.add(plan1)
    db.commit()

    s1 = StudySession(
        study_plan_id=plan1.id,
        lesson_id=l1.id,
        session_date=date.today() - timedelta(days=2),
        start_time="18:00",
        end_time="18:40",
        duration_minutes=40,
        status="completed",
    )
    s2 = StudySession(
        study_plan_id=plan1.id,
        lesson_id=l2.id,
        session_date=date.today() - timedelta(days=1),
        start_time="18:00",
        end_time="18:50",
        duration_minutes=50,
        status="completed",
    )
    s3 = StudySession(
        study_plan_id=plan1.id,
        lesson_id=l3.id,
        session_date=date.today() + timedelta(days=1),
        start_time="18:00",
        end_time="19:00",
        duration_minutes=60,
        status="scheduled",
    )
    s4 = StudySession(
        study_plan_id=plan1.id,
        lesson_id=l1.id,
        session_date=date.today() - timedelta(days=3),
        start_time="17:00",
        end_time="17:30",
        duration_minutes=30,
        status="missed",
    )
    db.add_all([s1, s2, s3, s4])
    db.commit()

    # 7. Student 1 Mastery in Course 1:
    # 3 concepts:
    # - "Trees": score 90.0 (mastered)
    # - "Recursion": score 70.0 (developing)
    # - "Graphs": score 40.0 (weak)
    m_trees = UserMastery(user_id=student1.id, course_id=course1.id, lesson_id=l1.id, concept="Trees", mastery_score=90.0, status="mastered")
    m_rec = UserMastery(user_id=student1.id, course_id=course1.id, lesson_id=l1.id, concept="Recursion", mastery_score=70.0, status="developing")
    m_graphs = UserMastery(user_id=student1.id, course_id=course1.id, lesson_id=l2.id, concept="Graphs", mastery_score=40.0, status="weak")
    db.add_all([m_trees, m_rec, m_graphs])
    db.commit()

    # 8. Student 2 in Course 2 (isolation test):
    # Student 2 has high activity in Course 2, but 0 activity in Course 1
    m2 = Module(course_id=course2.id, title="Biology Module 1", order_number=1)
    db.add(m2)
    db.commit()
    l_bio = Lesson(module_id=m2.id, title="Cell Division", order_number=1, estimated_minutes=30)
    db.add(l_bio)
    db.commit()

    m_bio = UserMastery(user_id=student2.id, course_id=course2.id, lesson_id=l_bio.id, concept="Mitosis", mastery_score=95.0, status="mastered")
    db.add(m_bio)
    db.commit()

    return {
        "teacher": teacher,
        "student1": student1,
        "student2": student2,
        "course1": course1,
        "course2": course2,
        "lessons_c1": [l1, l2, l3],
        "quizzes_c1": [q1, q2],
    }


# ===========================================================================
# Test Cases
# ===========================================================================

def test_analytics_status_endpoint(client: TestClient):
    """11. GET /api/analytics/ returns ready status."""
    res = client.get("/api/analytics/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert "Analytics" in data["service"]


def test_successful_student_course_analytics(client: TestClient, test_db):
    """1. GET /api/analytics/user/{user_id}/course/{course_id} returns 200 with full structure."""
    data = seed_analytics_data(test_db)
    student1 = data["student1"]
    course1 = data["course1"]

    res = client.get(f"/api/analytics/user/{student1.id}/course/{course1.id}")
    assert res.status_code == 200
    payload = res.json()

    assert payload["user_id"] == student1.id
    assert payload["course_id"] == course1.id
    assert "course_progress" in payload
    assert "quiz_performance" in payload
    assert "mastery" in payload
    assert "study_activity" in payload


def test_correct_lesson_progress_calculation(client: TestClient, test_db):
    """2. Validates course_progress: total_lessons, completed_lessons, and completion_percentage."""
    data = seed_analytics_data(test_db)
    student1 = data["student1"]
    course1 = data["course1"]

    res = client.get(f"/api/analytics/user/{student1.id}/course/{course1.id}")
    assert res.status_code == 200
    prog = res.json()["course_progress"]

    # Course 1 has 3 lessons: Lesson 1 & 2 have completed sessions, Lesson 3 does not
    assert prog["total_lessons"] == 3
    assert prog["completed_lessons"] == 2
    # 2/3 = 66.7%
    assert pytest.approx(prog["completion_percentage"], 0.1) == 66.7


def test_correct_quiz_performance_calculation(client: TestClient, test_db):
    """3. Validates quiz_performance: attempted, average, best, passed, and pass_rate."""
    data = seed_analytics_data(test_db)
    student1 = data["student1"]
    course1 = data["course1"]

    res = client.get(f"/api/analytics/user/{student1.id}/course/{course1.id}")
    assert res.status_code == 200
    qp = res.json()["quiz_performance"]

    # Student 1 has 2 submissions: 100% (passed) and 50% (failed)
    assert qp["quizzes_attempted"] == 2
    assert qp["average_score"] == 75.0
    assert qp["best_score"] == 100.0
    assert qp["passed_quizzes"] == 1
    assert qp["pass_rate"] == 50.0


def test_correct_mastery_calculation(client: TestClient, test_db):
    """4. Validates mastery: total, mastered, developing, weak, overall, and weak_topics."""
    data = seed_analytics_data(test_db)
    student1 = data["student1"]
    course1 = data["course1"]

    res = client.get(f"/api/analytics/user/{student1.id}/course/{course1.id}")
    assert res.status_code == 200
    m = res.json()["mastery"]

    # Concepts: Trees (90%), Recursion (70%), Graphs (40%)
    assert m["total_concepts"] == 3
    assert m["mastered_concepts"] == 1
    assert m["developing_concepts"] == 1
    assert m["weak_concepts"] == 1
    # Average = (90 + 70 + 40) / 3 = 66.7
    assert pytest.approx(m["overall_mastery"], 0.1) == 66.7
    assert m["weak_topics"] == ["Graphs"]


def test_correct_study_activity_calculation(client: TestClient, test_db):
    """5. Validates study_activity: planned minutes, completed minutes, and session counts."""
    data = seed_analytics_data(test_db)
    student1 = data["student1"]
    course1 = data["course1"]

    res = client.get(f"/api/analytics/user/{student1.id}/course/{course1.id}")
    assert res.status_code == 200
    act = res.json()["study_activity"]

    # Sessions: 40 (completed), 50 (completed), 60 (scheduled), 30 (missed)
    assert act["total_planned_minutes"] == 180
    assert act["completed_minutes"] == 90
    assert act["completed_sessions"] == 2
    assert act["missed_sessions"] == 1
    assert act["scheduled_sessions"] == 1


def test_user_and_course_404_handling(client: TestClient, test_db):
    """6. Returns HTTP 404 with descriptive detail when user or course does not exist."""
    data = seed_analytics_data(test_db)
    student1 = data["student1"]
    course1 = data["course1"]

    # Nonexistent user
    res_no_user = client.get(f"/api/analytics/user/99999/course/{course1.id}")
    assert res_no_user.status_code == 404
    assert "user with id 99999 not found" in res_no_user.json()["detail"].lower()

    # Nonexistent course
    res_no_course = client.get(f"/api/analytics/user/{student1.id}/course/88888")
    assert res_no_course.status_code == 404
    assert "course with id 88888 not found" in res_no_course.json()["detail"].lower()

    # Performance endpoint 404
    res_perf_404 = client.get(f"/api/analytics/user/99999/course/{course1.id}/performance")
    assert res_perf_404.status_code == 404

    # Overview endpoint 404
    res_over_404 = client.get(f"/api/analytics/user/{student1.id}/course/88888/overview")
    assert res_over_404.status_code == 404


def test_empty_no_activity_safe_response(client: TestClient, test_db):
    """7. Valid user and course with zero previous activity returns safe zero/empty analytics."""
    teacher = User(name="Empty Teacher", email="empty_teacher@test.com", role="teacher")
    student = User(name="New Student", email="new_student@test.com", role="student")
    test_db.add_all([teacher, student])
    test_db.commit()

    course = Course(title="Brand New Course", teacher_id=teacher.id)
    test_db.add(course)
    test_db.commit()

    # 1. Main analytics endpoint
    res = client.get(f"/api/analytics/user/{student.id}/course/{course.id}")
    assert res.status_code == 200
    payload = res.json()

    assert payload["course_progress"]["total_lessons"] == 0
    assert payload["course_progress"]["completed_lessons"] == 0
    assert payload["course_progress"]["completion_percentage"] == 0.0

    assert payload["quiz_performance"]["quizzes_attempted"] == 0
    assert payload["quiz_performance"]["average_score"] == 0.0
    assert payload["quiz_performance"]["best_score"] == 0.0
    assert payload["quiz_performance"]["passed_quizzes"] == 0
    assert payload["quiz_performance"]["pass_rate"] == 0.0

    assert payload["mastery"]["total_concepts"] == 0
    assert payload["mastery"]["mastered_concepts"] == 0
    assert payload["mastery"]["developing_concepts"] == 0
    assert payload["mastery"]["weak_concepts"] == 0
    assert payload["mastery"]["overall_mastery"] == 0.0
    assert payload["mastery"]["weak_topics"] == []

    assert payload["study_activity"]["total_planned_minutes"] == 0
    assert payload["study_activity"]["completed_minutes"] == 0
    assert payload["study_activity"]["completed_sessions"] == 0
    assert payload["study_activity"]["missed_sessions"] == 0
    assert payload["study_activity"]["scheduled_sessions"] == 0

    # 2. Performance history endpoint
    res_perf = client.get(f"/api/analytics/user/{student.id}/course/{course.id}/performance")
    assert res_perf.status_code == 200
    assert res_perf.json() == []

    # 3. Overview endpoint
    res_over = client.get(f"/api/analytics/user/{student.id}/course/{course.id}/overview")
    assert res_over.status_code == 200
    over = res_over.json()
    assert over["course_progress_percentage"] == 0.0
    assert over["average_quiz_score"] == 0.0
    assert over["overall_mastery"] == 0.0
    assert over["completed_study_minutes"] == 0
    assert over["weak_topics"] == []


def test_strict_user_and_course_isolation(client: TestClient, test_db):
    """8. Ensures data is scoped strictly to requested user AND course without leakage."""
    data = seed_analytics_data(test_db)
    student1 = data["student1"]
    student2 = data["student2"]
    course1 = data["course1"]
    course2 = data["course2"]

    # Student 2 in Course 1 has NO activity, despite Student 1 having extensive activity
    res_s2_c1 = client.get(f"/api/analytics/user/{student2.id}/course/{course1.id}")
    assert res_s2_c1.status_code == 200
    p2 = res_s2_c1.json()
    assert p2["course_progress"]["completed_lessons"] == 0
    assert p2["quiz_performance"]["quizzes_attempted"] == 0
    assert p2["mastery"]["total_concepts"] == 0
    assert p2["study_activity"]["completed_sessions"] == 0

    # Student 1 in Course 2 has NO activity, despite Student 2 having mastery in Course 2
    res_s1_c2 = client.get(f"/api/analytics/user/{student1.id}/course/{course2.id}")
    assert res_s1_c2.status_code == 200
    p1 = res_s1_c2.json()
    assert p1["mastery"]["total_concepts"] == 0
    assert p1["mastery"]["overall_mastery"] == 0.0

    # Performance history isolation
    res_perf_s2 = client.get(f"/api/analytics/user/{student2.id}/course/{course1.id}/performance")
    assert res_perf_s2.status_code == 200
    assert res_perf_s2.json() == []


def test_student_analytics_do_not_expose_quiz_answers(client: TestClient, test_db):
    """9. CRITICAL SECURITY: Performance history never leaks correct_answer, explanation, answers, or feedback."""
    data = seed_analytics_data(test_db)
    student1 = data["student1"]
    course1 = data["course1"]

    res = client.get(f"/api/analytics/user/{student1.id}/course/{course1.id}/performance")
    assert res.status_code == 200
    records = res.json()

    assert len(records) == 2
    forbidden_keys = {"correct_answer", "correct_answers", "explanation", "explanations", "answers", "feedback", "answer_key"}

    for item in records:
        assert "quiz_id" in item
        assert "score" in item
        assert "percentage" in item
        assert "passed" in item
        assert "submitted_at" in item
        assert "submission_id" in item
        assert "quiz_title" in item

        # Verify absolutely zero answer key or internal feedback leakage
        item_keys = set(item.keys())
        leakage = item_keys.intersection(forbidden_keys)
        assert not leakage, f"Forbidden answer fields leaked in analytics performance: {leakage}"

        # Check values do not contain teacher explanation
        item_str = str(item)
        assert "Secret teacher explanation" not in item_str


def test_overview_endpoint(client: TestClient, test_db):
    """10. GET /api/analytics/user/{user_id}/course/{course_id}/overview returns compact dashboard metrics."""
    data = seed_analytics_data(test_db)
    student1 = data["student1"]
    course1 = data["course1"]

    res = client.get(f"/api/analytics/user/{student1.id}/course/{course1.id}/overview")
    assert res.status_code == 200
    over = res.json()

    assert over["user_id"] == student1.id
    assert over["course_id"] == course1.id
    assert pytest.approx(over["course_progress_percentage"], 0.1) == 66.7
    assert pytest.approx(over["completion_percentage"], 0.1) == 66.7
    assert over["average_quiz_score"] == 75.0
    assert pytest.approx(over["overall_mastery"], 0.1) == 66.7
    assert over["mastered_concepts"] == 1
    assert over["developing_concepts"] == 1
    assert over["weak_concepts"] == 1
    assert over["completed_study_minutes"] == 90
    assert over["completed_minutes"] == 90
    assert over["completed_sessions"] == 2
    assert over["missed_sessions"] == 1
    assert over["weak_topics"] == ["Graphs"]
