"""
tests/test_study_planner.py - Phase 5 Step 5 Tests: AI Study Planner & Deterministic Personalized Timetable Generation.
"""

from datetime import date, datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from database.models import (
    User,
    Course,
    Module,
    Lesson,
    UserMastery,
    StudyPreference,
    StudyPlan,
    StudySession,
)
from ai.study_planner import (
    calculate_available_dates,
    calculate_lesson_priority,
    split_lesson_into_chunks,
    build_revision_chunks,
    time_str_to_minutes,
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
    PRIORITY_LOW,
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_MISSED,
    SESSION_STATUS_SCHEDULED,
)
from tests.conftest import TestingSessionLocal


@pytest.fixture
def test_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_planner_fixture(db, num_lessons: int = 3) -> tuple:
    """Helper creating teacher, student, course, module, and lessons."""
    teacher = User(name="Teacher Jane", email="jane_teacher@test.com", role="teacher")
    student = User(name="Student Bob", email="bob_student@test.com", role="student")
    db.add_all([teacher, student])
    db.commit()
    db.refresh(teacher)
    db.refresh(student)

    course = Course(title="Algorithms 101", teacher_id=teacher.id)
    db.add(course)
    db.commit()
    db.refresh(course)

    module = Module(title="Core Algorithms", course_id=course.id, order_number=1)
    db.add(module)
    db.commit()
    db.refresh(module)

    lessons = []
    difficulties = ["beginner", "intermediate", "advanced"]
    durations = [30, 45, 60]
    for i in range(1, num_lessons + 1):
        diff = difficulties[(i - 1) % len(difficulties)]
        dur = durations[(i - 1) % len(durations)]
        lesson = Lesson(
            title=f"Lesson {i}",
            module_id=module.id,
            order_number=i,
            estimated_minutes=dur,
            difficulty=diff,
            key_concepts=[f"Concept {i}"],
        )
        db.add(lesson)
        lessons.append(lesson)

    db.commit()
    for l in lessons:
        db.refresh(l)

    return teacher, student, course, module, lessons


# --- Test Cases ---

def test_preferences_can_be_created(client: TestClient, test_db):
    """1. Preferences can be successfully created with valid data."""
    _, student, course, _, _ = create_planner_fixture(test_db)
    exam_dt = (date.today() + timedelta(days=14)).isoformat()

    payload = {
        "exam_date": exam_dt,
        "daily_study_limit_minutes": 120,
        "available_days": ["monday", "wednesday", "friday"],
        "availability_windows": [
            {"start": "18:00", "end": "20:00"}
        ],
        "preferred_session_minutes": 60,
    }

    res = client.put(f"/api/planner/user/{student.id}/course/{course.id}/preferences", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["user_id"] == student.id
    assert data["course_id"] == course.id
    assert data["daily_study_limit_minutes"] == 120
    assert data["available_days"] == ["monday", "wednesday", "friday"]
    assert len(data["availability_windows"]) == 1


def test_preferences_update_instead_of_duplicate(client: TestClient, test_db):
    """2. Updating preferences updates the existing record rather than creating a duplicate."""
    _, student, course, _, _ = create_planner_fixture(test_db)
    exam_dt1 = (date.today() + timedelta(days=14)).isoformat()
    exam_dt2 = (date.today() + timedelta(days=21)).isoformat()

    payload1 = {
        "exam_date": exam_dt1,
        "daily_study_limit_minutes": 120,
        "available_days": ["monday", "wednesday"],
        "availability_windows": [{"start": "18:00", "end": "20:00"}],
        "preferred_session_minutes": 60,
    }
    res1 = client.put(f"/api/planner/user/{student.id}/course/{course.id}/preferences", json=payload1)
    assert res1.status_code == 200

    payload2 = {
        "exam_date": exam_dt2,
        "daily_study_limit_minutes": 90,
        "available_days": ["tuesday", "thursday"],
        "availability_windows": [{"start": "19:00", "end": "20:30"}],
        "preferred_session_minutes": 45,
    }
    res2 = client.put(f"/api/planner/user/{student.id}/course/{course.id}/preferences", json=payload2)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["daily_study_limit_minutes"] == 90
    assert data2["available_days"] == ["tuesday", "thursday"]

    # Verify only one preference record exists in DB
    test_db.expire_all()
    count = test_db.query(StudyPreference).filter(
        StudyPreference.user_id == student.id,
        StudyPreference.course_id == course.id,
    ).count()
    assert count == 1


def test_invalid_user_returns_404(client: TestClient, test_db):
    """3. Invalid user returns 404."""
    _, _, course, _, _ = create_planner_fixture(test_db)
    exam_dt = (date.today() + timedelta(days=14)).isoformat()
    payload = {
        "exam_date": exam_dt,
        "daily_study_limit_minutes": 120,
        "available_days": ["monday"],
        "availability_windows": [{"start": "18:00", "end": "20:00"}],
        "preferred_session_minutes": 60,
    }
    res = client.put(f"/api/planner/user/99999/course/{course.id}/preferences", json=payload)
    assert res.status_code == 404

    res_gen = client.post(f"/api/planner/user/99999/course/{course.id}/generate")
    assert res_gen.status_code == 404

    res_get = client.get(f"/api/planner/user/99999/course/{course.id}")
    assert res_get.status_code == 404


def test_invalid_course_returns_404(client: TestClient, test_db):
    """4. Invalid course returns 404."""
    _, student, _, _, _ = create_planner_fixture(test_db)
    exam_dt = (date.today() + timedelta(days=14)).isoformat()
    payload = {
        "exam_date": exam_dt,
        "daily_study_limit_minutes": 120,
        "available_days": ["monday"],
        "availability_windows": [{"start": "18:00", "end": "20:00"}],
        "preferred_session_minutes": 60,
    }
    res = client.put(f"/api/planner/user/{student.id}/course/99999/preferences", json=payload)
    assert res.status_code == 404

    res_gen = client.post(f"/api/planner/user/{student.id}/course/99999/generate")
    assert res_gen.status_code == 404


def test_past_exam_date_rejected(client: TestClient, test_db):
    """5. Past exam date is rejected with 422 validation error."""
    _, student, course, _, _ = create_planner_fixture(test_db)
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    payload = {
        "exam_date": yesterday,
        "daily_study_limit_minutes": 120,
        "available_days": ["monday"],
        "availability_windows": [{"start": "18:00", "end": "20:00"}],
        "preferred_session_minutes": 60,
    }
    res = client.put(f"/api/planner/user/{student.id}/course/{course.id}/preferences", json=payload)
    assert res.status_code == 422


def test_invalid_weekday_rejected(client: TestClient, test_db):
    """6. Invalid weekday name is rejected."""
    _, student, course, _, _ = create_planner_fixture(test_db)
    exam_dt = (date.today() + timedelta(days=14)).isoformat()

    payload = {
        "exam_date": exam_dt,
        "daily_study_limit_minutes": 120,
        "available_days": ["funday"],
        "availability_windows": [{"start": "18:00", "end": "20:00"}],
        "preferred_session_minutes": 60,
    }
    res = client.put(f"/api/planner/user/{student.id}/course/{course.id}/preferences", json=payload)
    assert res.status_code == 422


def test_duplicate_weekday_rejected(client: TestClient, test_db):
    """7. Duplicate weekday names are rejected."""
    _, student, course, _, _ = create_planner_fixture(test_db)
    exam_dt = (date.today() + timedelta(days=14)).isoformat()

    payload = {
        "exam_date": exam_dt,
        "daily_study_limit_minutes": 120,
        "available_days": ["monday", "monday"],
        "availability_windows": [{"start": "18:00", "end": "20:00"}],
        "preferred_session_minutes": 60,
    }
    res = client.put(f"/api/planner/user/{student.id}/course/{course.id}/preferences", json=payload)
    assert res.status_code == 422


def test_invalid_availability_window_rejected(client: TestClient, test_db):
    """8. Window with start >= end is rejected."""
    _, student, course, _, _ = create_planner_fixture(test_db)
    exam_dt = (date.today() + timedelta(days=14)).isoformat()

    payload = {
        "exam_date": exam_dt,
        "daily_study_limit_minutes": 120,
        "available_days": ["monday"],
        "availability_windows": [{"start": "20:00", "end": "18:00"}],
        "preferred_session_minutes": 60,
    }
    res = client.put(f"/api/planner/user/{student.id}/course/{course.id}/preferences", json=payload)
    assert res.status_code == 422


def test_preferred_session_greater_than_daily_limit_rejected(client: TestClient, test_db):
    """9. Preferred session > daily limit is rejected."""
    _, student, course, _, _ = create_planner_fixture(test_db)
    exam_dt = (date.today() + timedelta(days=14)).isoformat()

    payload = {
        "exam_date": exam_dt,
        "daily_study_limit_minutes": 60,
        "available_days": ["monday"],
        "availability_windows": [{"start": "18:00", "end": "20:00"}],
        "preferred_session_minutes": 90,
    }
    res = client.put(f"/api/planner/user/{student.id}/course/{course.id}/preferences", json=payload)
    assert res.status_code == 422


def test_available_dates_respect_weekdays(client: TestClient, test_db):
    """10. Available dates strictly respect the selected weekdays."""
    start = date(2026, 10, 1)  # Thursday
    exam = date(2026, 10, 15)  # Thursday
    weekdays = ["monday", "wednesday"]

    dates = calculate_available_dates(start, exam, weekdays)
    for d in dates:
        assert d.strftime("%A").lower() in weekdays
        assert d < exam


def test_sessions_stay_inside_availability_windows(client: TestClient, test_db):
    """11. Scheduled sessions stay completely inside configured availability windows."""
    _, student, course, _, _ = create_planner_fixture(test_db)
    exam_dt = (date.today() + timedelta(days=14)).isoformat()

    client.put(
        f"/api/planner/user/{student.id}/course/{course.id}/preferences",
        json={
            "exam_date": exam_dt,
            "daily_study_limit_minutes": 120,
            "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            "availability_windows": [{"start": "18:00", "end": "20:00"}],
            "preferred_session_minutes": 60,
        },
    )

    res = client.post(f"/api/planner/user/{student.id}/course/{course.id}/generate")
    assert res.status_code == 200, res.text
    sessions = res.json()["sessions"]
    assert len(sessions) > 0

    w_start = time_str_to_minutes("18:00")
    w_end = time_str_to_minutes("20:00")

    for s in sessions:
        s_start = time_str_to_minutes(s["start_time"])
        s_end = time_str_to_minutes(s["end_time"])
        assert s_start >= w_start, f"Session starts before window: {s['start_time']}"
        assert s_end <= w_end, f"Session ends after window: {s['end_time']}"


def test_daily_study_limit_never_exceeded(client: TestClient, test_db):
    """12. Total scheduled duration on any day never exceeds daily_study_limit_minutes."""
    _, student, course, _, _ = create_planner_fixture(test_db, num_lessons=5)
    exam_dt = (date.today() + timedelta(days=20)).isoformat()

    daily_limit = 90
    client.put(
        f"/api/planner/user/{student.id}/course/{course.id}/preferences",
        json={
            "exam_date": exam_dt,
            "daily_study_limit_minutes": daily_limit,
            "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            "availability_windows": [{"start": "09:00", "end": "17:00"}],  # 8 hour window
            "preferred_session_minutes": 45,
        },
    )

    res = client.post(f"/api/planner/user/{student.id}/course/{course.id}/generate")
    assert res.status_code == 200
    sessions = res.json()["sessions"]

    day_totals = {}
    for s in sessions:
        day_totals[s["session_date"]] = day_totals.get(s["session_date"], 0) + s["duration_minutes"]

    for d_str, total in day_totals.items():
        assert total <= daily_limit, f"Day {d_str} scheduled {total} mins > {daily_limit}"


def test_no_overlapping_sessions(client: TestClient, test_db):
    """13. Sessions on the same date never overlap."""
    _, student, course, _, _ = create_planner_fixture(test_db, num_lessons=4)
    exam_dt = (date.today() + timedelta(days=14)).isoformat()

    client.put(
        f"/api/planner/user/{student.id}/course/{course.id}/preferences",
        json={
            "exam_date": exam_dt,
            "daily_study_limit_minutes": 180,
            "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            "availability_windows": [
                {"start": "10:00", "end": "12:00"},
                {"start": "14:00", "end": "16:00"},
            ],
            "preferred_session_minutes": 60,
        },
    )

    res = client.post(f"/api/planner/user/{student.id}/course/{course.id}/generate")
    assert res.status_code == 200
    sessions = res.json()["sessions"]

    by_date = {}
    for s in sessions:
        by_date.setdefault(s["session_date"], []).append(s)

    for d_str, day_sessions in by_date.items():
        sorted_s = sorted(day_sessions, key=lambda s: time_str_to_minutes(s["start_time"]))
        for i in range(len(sorted_s) - 1):
            cur_end = time_str_to_minutes(sorted_s[i]["end_time"])
            next_start = time_str_to_minutes(sorted_s[i + 1]["start_time"])
            assert cur_end <= next_start, f"Overlap detected on {d_str}: {sorted_s[i]} and {sorted_s[i+1]}"


def test_long_lessons_split_correctly(test_db):
    """14. Lessons longer than preferred session minutes split into appropriate chunks."""
    lesson = Lesson(
        title="Deep Dive into Sorting",
        module_id=1,
        order_number=1,
        estimated_minutes=90,
    )
    chunks = split_lesson_into_chunks(lesson, priority=PRIORITY_MEDIUM, preferred_session_minutes=60)
    assert len(chunks) == 2
    assert chunks[0]["duration"] == 60
    assert chunks[1]["duration"] == 30
    assert chunks[0]["type"] == "lesson"


def test_completed_lessons_not_scheduled_as_new_lessons(client: TestClient, test_db):
    """15. Completed lessons are excluded from new lesson scheduling."""
    _, student, course, _, lessons = create_planner_fixture(test_db, num_lessons=3)
    exam_dt = (date.today() + timedelta(days=14)).isoformat()

    client.put(
        f"/api/planner/user/{student.id}/course/{course.id}/preferences",
        json={
            "exam_date": exam_dt,
            "daily_study_limit_minutes": 120,
            "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            "availability_windows": [{"start": "18:00", "end": "20:00"}],
            "preferred_session_minutes": 60,
        },
    )

    # Explicitly mark Lesson 1 as completed
    completed_id = lessons[0].id
    res = client.post(
        f"/api/planner/user/{student.id}/course/{course.id}/generate",
        json={"completed_lesson_ids": [completed_id]},
    )
    assert res.status_code == 200
    sessions = res.json()["sessions"]

    # Lesson 1 should not appear as a 'lesson' type session
    new_lesson_ids = [s["lesson_id"] for s in sessions if s["session_type"] == "lesson"]
    assert completed_id not in new_lesson_ids


def test_weak_concepts_receive_higher_priority(test_db):
    """16. Lessons with weak concepts (< 60%) receive high priority."""
    lesson = Lesson(
        id=101,
        title="Graph Traversal",
        module_id=1,
        order_number=1,
        estimated_minutes=30,
        difficulty="beginner",
        key_concepts=["Graphs"],
    )

    weak_mastery = UserMastery(
        user_id=1,
        course_id=1,
        concept="Graphs",
        mastery_score=40.0,
        status="weak",
    )
    mastery_by_concept = {"graphs": weak_mastery}

    score, priority = calculate_lesson_priority(lesson, mastery_by_concept, {})
    assert priority == PRIORITY_HIGH


def test_difficult_lessons_receive_priority_adjustment(test_db):
    """17. Difficult lessons receive a positive numeric priority adjustment."""
    lesson_easy = Lesson(
        id=1,
        title="Intro",
        module_id=1,
        order_number=1,
        estimated_minutes=30,
        difficulty="beginner",
        key_concepts=[],
    )
    lesson_hard = Lesson(
        id=2,
        title="Advanced DP",
        module_id=1,
        order_number=2,
        estimated_minutes=30,
        difficulty="hard",
        key_concepts=[],
    )

    score_easy, _ = calculate_lesson_priority(lesson_easy, {}, {})
    score_hard, _ = calculate_lesson_priority(lesson_hard, {}, {})

    assert score_hard > score_easy


def test_revision_targets_weak_and_developing_concepts(test_db):
    """18. Revision session allocation prioritizes weak and developing concepts."""
    l_weak = Lesson(id=1, title="Weak Lesson", module_id=1, key_concepts=["Trees"], estimated_minutes=30)
    l_mastered = Lesson(id=2, title="Mastered Lesson", module_id=1, key_concepts=["Arrays"], estimated_minutes=30)

    m_weak = UserMastery(concept="Trees", mastery_score=35.0, status="weak")
    m_mastered = UserMastery(concept="Arrays", mastery_score=95.0, status="mastered")

    mastery_map = {"trees": m_weak, "arrays": m_mastered}

    rev_chunks = build_revision_chunks(
        all_lessons=[l_mastered, l_weak],
        mastery_by_concept=mastery_map,
        mastery_by_lesson_id={},
        allowed_revision_capacity=30,
        preferred_session_minutes=30,
    )

    assert len(rev_chunks) == 1
    assert rev_chunks[0]["lesson_id"] == l_weak.id
    assert rev_chunks[0]["priority"] == PRIORITY_HIGH
    assert rev_chunks[0]["type"] == "revision"


def test_plan_generation_creates_study_plan(client: TestClient, test_db):
    """19. Generating a plan creates a persistent StudyPlan record."""
    _, student, course, _, _ = create_planner_fixture(test_db)
    exam_dt = (date.today() + timedelta(days=14)).isoformat()

    client.put(
        f"/api/planner/user/{student.id}/course/{course.id}/preferences",
        json={
            "exam_date": exam_dt,
            "daily_study_limit_minutes": 120,
            "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            "availability_windows": [{"start": "18:00", "end": "20:00"}],
            "preferred_session_minutes": 60,
        },
    )

    res = client.post(f"/api/planner/user/{student.id}/course/{course.id}/generate")
    assert res.status_code == 200
    plan_data = res.json()
    assert plan_data["user_id"] == student.id
    assert plan_data["course_id"] == course.id
    assert plan_data["status"] == "active"
    assert plan_data["total_planned_minutes"] > 0


def test_study_sessions_persisted(client: TestClient, test_db):
    """20. Scheduled sessions are persisted directly in the database."""
    _, student, course, _, _ = create_planner_fixture(test_db)
    exam_dt = (date.today() + timedelta(days=14)).isoformat()

    client.put(
        f"/api/planner/user/{student.id}/course/{course.id}/preferences",
        json={
            "exam_date": exam_dt,
            "daily_study_limit_minutes": 120,
            "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            "availability_windows": [{"start": "18:00", "end": "20:00"}],
            "preferred_session_minutes": 60,
        },
    )

    res = client.post(f"/api/planner/user/{student.id}/course/{course.id}/generate")
    plan_id = res.json()["id"]

    test_db.expire_all()
    sessions = test_db.query(StudySession).filter(StudySession.study_plan_id == plan_id).all()
    assert len(sessions) > 0


def test_regeneration_does_not_duplicate_plans_or_sessions(client: TestClient, test_db):
    """21. Repeated plan generation updates active plan in place without duplicating plans or sessions."""
    _, student, course, _, _ = create_planner_fixture(test_db)
    exam_dt = (date.today() + timedelta(days=14)).isoformat()

    client.put(
        f"/api/planner/user/{student.id}/course/{course.id}/preferences",
        json={
            "exam_date": exam_dt,
            "daily_study_limit_minutes": 120,
            "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            "availability_windows": [{"start": "18:00", "end": "20:00"}],
            "preferred_session_minutes": 60,
        },
    )

    res1 = client.post(f"/api/planner/user/{student.id}/course/{course.id}/generate")
    plan1 = res1.json()

    res2 = client.post(f"/api/planner/user/{student.id}/course/{course.id}/generate")
    plan2 = res2.json()

    assert plan1["id"] == plan2["id"]

    test_db.expire_all()
    plan_count = test_db.query(StudyPlan).filter(
        StudyPlan.user_id == student.id,
        StudyPlan.course_id == course.id,
        StudyPlan.status == "active",
    ).count()
    assert plan_count == 1


def test_today_endpoint_returns_only_today_sessions(client: TestClient, test_db):
    """22. GET /today returns only sessions scheduled for date.today()."""
    _, student, course, _, _ = create_planner_fixture(test_db)
    exam_dt = (date.today() + timedelta(days=14)).isoformat()
    today_weekday = date.today().strftime("%A").lower()

    client.put(
        f"/api/planner/user/{student.id}/course/{course.id}/preferences",
        json={
            "exam_date": exam_dt,
            "daily_study_limit_minutes": 120,
            "available_days": [today_weekday],
            "availability_windows": [{"start": "18:00", "end": "20:00"}],
            "preferred_session_minutes": 60,
        },
    )

    client.post(f"/api/planner/user/{student.id}/course/{course.id}/generate")

    res = client.get(f"/api/planner/user/{student.id}/course/{course.id}/today")
    assert res.status_code == 200
    sessions = res.json()
    today_iso = date.today().isoformat()
    for s in sessions:
        assert s["session_date"] == today_iso


def test_upcoming_endpoint_sorts_correctly(client: TestClient, test_db):
    """23. GET /upcoming returns future sessions sorted by session_date ASC, start_time ASC."""
    _, student, course, _, _ = create_planner_fixture(test_db, num_lessons=4)
    exam_dt = (date.today() + timedelta(days=14)).isoformat()

    client.put(
        f"/api/planner/user/{student.id}/course/{course.id}/preferences",
        json={
            "exam_date": exam_dt,
            "daily_study_limit_minutes": 60,
            "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            "availability_windows": [{"start": "18:00", "end": "20:00"}],
            "preferred_session_minutes": 60,
        },
    )

    client.post(f"/api/planner/user/{student.id}/course/{course.id}/generate")

    res = client.get(f"/api/planner/user/{student.id}/course/{course.id}/upcoming")
    assert res.status_code == 200
    sessions = res.json()
    assert len(sessions) > 0

    for i in range(len(sessions) - 1):
        cur_dt = sessions[i]["session_date"]
        next_dt = sessions[i + 1]["session_date"]
        if cur_dt == next_dt:
            assert sessions[i]["start_time"] <= sessions[i + 1]["start_time"]
        else:
            assert cur_dt <= next_dt


def test_missing_preferences_handled_correctly(client: TestClient, test_db):
    """24. Calling generate without preferences returns 400 Bad Request."""
    _, student, course, _, _ = create_planner_fixture(test_db)

    res = client.post(f"/api/planner/user/{student.id}/course/{course.id}/generate")
    assert res.status_code == 400
    assert "preferences" in res.json()["detail"].lower()


def test_course_with_no_lessons_handled_correctly(client: TestClient, test_db):
    """25. Course with no lessons returns 400 Bad Request."""
    teacher = User(name="Teacher Empty", email="empty_teacher@test.com", role="teacher")
    student = User(name="Student Empty", email="empty_student@test.com", role="student")
    test_db.add_all([teacher, student])
    test_db.commit()

    empty_course = Course(title="Empty Course", teacher_id=teacher.id)
    test_db.add(empty_course)
    test_db.commit()

    exam_dt = (date.today() + timedelta(days=14)).isoformat()
    client.put(
        f"/api/planner/user/{student.id}/course/{empty_course.id}/preferences",
        json={
            "exam_date": exam_dt,
            "daily_study_limit_minutes": 120,
            "available_days": ["monday"],
            "availability_windows": [{"start": "18:00", "end": "20:00"}],
            "preferred_session_minutes": 60,
        },
    )

    res = client.post(f"/api/planner/user/{student.id}/course/{empty_course.id}/generate")
    assert res.status_code == 400
    assert "no lessons" in res.json()["detail"].lower()


def test_insufficient_capacity_handled_correctly(client: TestClient, test_db):
    """26. Insufficient capacity before exam deadline returns clear 400 Bad Request."""
    _, student, course, _, _ = create_planner_fixture(test_db, num_lessons=5)  # Needs > 150 mins
    # Only 1 day available with 30 min limit = 30 mins capacity < 150 mins needed
    tomorrow = (date.today() + timedelta(days=1))
    day_after = (date.today() + timedelta(days=2))
    weekday = tomorrow.strftime("%A").lower()

    client.put(
        f"/api/planner/user/{student.id}/course/{course.id}/preferences",
        json={
            "exam_date": day_after.isoformat(),
            "daily_study_limit_minutes": 30,
            "available_days": [weekday],
            "availability_windows": [{"start": "18:00", "end": "18:30"}],
            "preferred_session_minutes": 30,
        },
    )

    res = client.post(
        f"/api/planner/user/{student.id}/course/{course.id}/generate",
        json={"start_date": tomorrow.isoformat()},
    )
    assert res.status_code == 400
    assert "too soon" in res.json()["detail"].lower()


def test_session_status_can_be_updated(client: TestClient, test_db):
    """27. PATCH /api/planner/sessions/{session_id} updates status."""
    _, student, course, _, _ = create_planner_fixture(test_db)
    exam_dt = (date.today() + timedelta(days=14)).isoformat()

    client.put(
        f"/api/planner/user/{student.id}/course/{course.id}/preferences",
        json={
            "exam_date": exam_dt,
            "daily_study_limit_minutes": 120,
            "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            "availability_windows": [{"start": "18:00", "end": "20:00"}],
            "preferred_session_minutes": 60,
        },
    )

    plan_res = client.post(f"/api/planner/user/{student.id}/course/{course.id}/generate")
    session_id = plan_res.json()["sessions"][0]["id"]

    patch_res = client.patch(f"/api/planner/sessions/{session_id}", json={"status": "completed"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "completed"


def test_invalid_session_status_rejected(client: TestClient, test_db):
    """28. PATCH /api/planner/sessions/{session_id} with invalid status returns 422."""
    _, student, course, _, _ = create_planner_fixture(test_db)
    exam_dt = (date.today() + timedelta(days=14)).isoformat()

    client.put(
        f"/api/planner/user/{student.id}/course/{course.id}/preferences",
        json={
            "exam_date": exam_dt,
            "daily_study_limit_minutes": 120,
            "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            "availability_windows": [{"start": "18:00", "end": "20:00"}],
            "preferred_session_minutes": 60,
        },
    )

    plan_res = client.post(f"/api/planner/user/{student.id}/course/{course.id}/generate")
    session_id = plan_res.json()["sessions"][0]["id"]

    patch_res = client.patch(f"/api/planner/sessions/{session_id}", json={"status": "cancelled"})
    assert patch_res.status_code == 422


def test_completed_and_missed_sessions_preserved_during_regeneration(client: TestClient, test_db):
    """29. Completed and missed sessions are preserved when plan is regenerated."""
    _, student, course, _, _ = create_planner_fixture(test_db)
    exam_dt = (date.today() + timedelta(days=14)).isoformat()

    client.put(
        f"/api/planner/user/{student.id}/course/{course.id}/preferences",
        json={
            "exam_date": exam_dt,
            "daily_study_limit_minutes": 120,
            "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            "availability_windows": [{"start": "18:00", "end": "20:00"}],
            "preferred_session_minutes": 60,
        },
    )

    plan1 = client.post(f"/api/planner/user/{student.id}/course/{course.id}/generate").json()
    first_session_id = plan1["sessions"][0]["id"]

    # Mark first session completed
    client.patch(f"/api/planner/sessions/{first_session_id}", json={"status": "completed"})

    # Regenerate plan
    plan2 = client.post(f"/api/planner/user/{student.id}/course/{course.id}/generate").json()

    test_db.expire_all()
    preserved = test_db.query(StudySession).filter(StudySession.id == first_session_id).first()
    assert preserved is not None
    assert preserved.status == "completed"


def test_no_mastery_records_produces_valid_deterministic_plan(client: TestClient, test_db):
    """30. A student with zero mastery records generates a valid deterministic schedule."""
    _, student, course, _, _ = create_planner_fixture(test_db)
    exam_dt = (date.today() + timedelta(days=14)).isoformat()

    client.put(
        f"/api/planner/user/{student.id}/course/{course.id}/preferences",
        json={
            "exam_date": exam_dt,
            "daily_study_limit_minutes": 120,
            "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            "availability_windows": [{"start": "18:00", "end": "20:00"}],
            "preferred_session_minutes": 60,
        },
    )

    res = client.post(f"/api/planner/user/{student.id}/course/{course.id}/generate")
    assert res.status_code == 200
    assert len(res.json()["sessions"]) > 0


def test_multiple_availability_windows_work(client: TestClient, test_db):
    """31. Timetable allocates across multiple daily windows (e.g. 10:00-11:00 and 14:00-15:00)."""
    _, student, course, _, _ = create_planner_fixture(test_db, num_lessons=4)
    exam_dt = (date.today() + timedelta(days=14)).isoformat()

    client.put(
        f"/api/planner/user/{student.id}/course/{course.id}/preferences",
        json={
            "exam_date": exam_dt,
            "daily_study_limit_minutes": 120,
            "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            "availability_windows": [
                {"start": "10:00", "end": "11:00"},
                {"start": "14:00", "end": "15:00"},
            ],
            "preferred_session_minutes": 60,
        },
    )

    res = client.post(f"/api/planner/user/{student.id}/course/{course.id}/generate")
    assert res.status_code == 200
    sessions = res.json()["sessions"]

    start_times = {s["start_time"] for s in sessions}
    # Should use both 10:00 and 14:00 windows
    assert "10:00" in start_times
    assert "14:00" in start_times


def test_student_planner_endpoints_do_not_leak_answers(client: TestClient, test_db):
    """32. Planner endpoints never expose quiz answers or grading keys."""
    _, student, course, _, _ = create_planner_fixture(test_db)
    exam_dt = (date.today() + timedelta(days=14)).isoformat()

    client.put(
        f"/api/planner/user/{student.id}/course/{course.id}/preferences",
        json={
            "exam_date": exam_dt,
            "daily_study_limit_minutes": 120,
            "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            "availability_windows": [{"start": "18:00", "end": "20:00"}],
            "preferred_session_minutes": 60,
        },
    )

    res = client.post(f"/api/planner/user/{student.id}/course/{course.id}/generate")
    data_str = res.text.lower()
    assert "correct_answer" not in data_str
    assert "explanation" not in data_str
    assert "answer_key" not in data_str


def test_availability_window_shorter_than_preferred_session(client: TestClient, test_db):
    """33. Availability window shorter than preferred session (e.g. 30 min window with 60 min preferred) allocates safely."""
    _, student, course, _, _ = create_planner_fixture(test_db, num_lessons=1)
    exam_dt = (date.today() + timedelta(days=14)).isoformat()

    client.put(
        f"/api/planner/user/{student.id}/course/{course.id}/preferences",
        json={
            "exam_date": exam_dt,
            "daily_study_limit_minutes": 60,
            "available_days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            "availability_windows": [{"start": "18:00", "end": "18:30"}],  # 30 mins
            "preferred_session_minutes": 60,
        },
    )

    res = client.post(f"/api/planner/user/{student.id}/course/{course.id}/generate")
    assert res.status_code == 200
    sessions = res.json()["sessions"]
    assert len(sessions) > 0
    assert sessions[0]["duration_minutes"] <= 30
