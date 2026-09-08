import logging
import math
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from database.models import User, Course, Module, Lesson, UserMastery, StudyPreference, StudyPlan, StudySession
from ai.mastery import (
    MASTERY_THRESHOLD_MASTERED,
    MASTERY_THRESHOLD_DEVELOPING,
    normalize_concept,
)

logger = logging.getLogger("lms.ai.study_planner")

# --- Centralized Constants ---
SESSION_TYPE_LESSON = "lesson"
SESSION_TYPE_REVISION = "revision"

SESSION_STATUS_SCHEDULED = "scheduled"
SESSION_STATUS_COMPLETED = "completed"
SESSION_STATUS_MISSED = "missed"

PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

REVISION_CAPACITY_RATIO = 0.20
DEFAULT_LESSON_MINUTES = 20


def time_str_to_minutes(t_str: str) -> int:
    """Converts 'HH:MM' string to minutes since midnight."""
    parts = t_str.strip().split(":")
    return int(parts[0]) * 60 + int(parts[1])


def minutes_to_time_str(m: int) -> str:
    """Converts minutes since midnight to 'HH:MM' format."""
    hours = (m // 60) % 24
    mins = m % 60
    return f"{hours:02d}:{mins:02d}"


def calculate_available_dates(
    start_date: date,
    exam_date: date,
    available_days: List[str],
) -> List[date]:
    """
    Calculates calendar dates available for studying from start_date through
    the day BEFORE exam_date matching available_days weekdays.
    
    Strictly excludes the exam_date itself so study completes beforehand.
    """
    if exam_date <= start_date:
        return []

    available_days_set = {d.strip().lower() for d in available_days}
    selected_dates: List[date] = []

    curr = start_date
    while curr < exam_date:
        weekday_name = curr.strftime("%A").lower()
        if weekday_name in available_days_set:
            selected_dates.append(curr)
        curr += timedelta(days=1)

    return selected_dates


def determine_completed_lessons(
    db: Session,
    user_id: int,
    course_id: int,
    explicit_completed_ids: Optional[List[int]] = None,
) -> Set[int]:
    """
    Determines completed lesson IDs for syllabus scheduling.
    
    A lesson is completed if:
    - Its ID is in explicit_completed_ids, OR
    - It has a StudySession with status="completed" for this user and course.
    
    Note: Quiz passage and concept mastery influence priority, but do NOT
    automatically mark a lesson as completed without an explicit record.
    """
    completed = set(explicit_completed_ids or [])

    # Find completed study sessions for this user/course
    session_rows = (
        db.query(StudySession.lesson_id)
        .join(StudyPlan, StudySession.study_plan_id == StudyPlan.id)
        .filter(
            StudyPlan.user_id == user_id,
            StudyPlan.course_id == course_id,
            StudySession.status == SESSION_STATUS_COMPLETED,
            StudySession.lesson_id.isnot(None),
        )
        .all()
    )
    for row in session_rows:
        if row[0] is not None:
            completed.add(row[0])

    return completed


def calculate_lesson_priority(
    lesson: Lesson,
    mastery_by_concept: Dict[str, UserMastery],
    mastery_by_lesson_id: Dict[int, List[UserMastery]],
) -> Tuple[int, str]:
    """
    Calculates a deterministic numerical priority score and categorical priority
    ('high', 'medium', 'low') for a lesson.
    
    Scoring:
    - Concept Mastery:
      - Any concept < 60% (weak): base = 30
      - Any concept 60-79% (developing): base = 20
      - All concepts >= 80% (mastered): base = 10
      - No mastery recorded (unstudied): base = 25
    - Difficulty adjustment:
      - hard / advanced: +10
      - medium / intermediate: +5
      - beginner / easy: +0
    - Duration adjustment:
      - > 45 mins: +5
      - > 30 mins: +3
    - Category mapping:
      - Any weak concept or score >= 35 -> 'high'
      - Score >= 20 -> 'medium'
      - Score < 20 -> 'low'
    """
    # 1. Gather mastery scores for this lesson
    scores: List[float] = []

    # Check direct lesson mastery
    if lesson.id in mastery_by_lesson_id:
        for m in mastery_by_lesson_id[lesson.id]:
            scores.append(m.mastery_score)

    # Check concept-level mastery from key_concepts
    if lesson.key_concepts and isinstance(lesson.key_concepts, list):
        for c in lesson.key_concepts:
            c_norm = normalize_concept(str(c))
            if c_norm:
                c_key = c_norm.lower()
                if c_key in mastery_by_concept:
                    scores.append(mastery_by_concept[c_key].mastery_score)
                elif c_norm in mastery_by_concept:
                    scores.append(mastery_by_concept[c_norm].mastery_score)

    # Determine base score from mastery
    has_weak = False
    if scores:
        min_score = min(scores)
        if min_score < MASTERY_THRESHOLD_DEVELOPING:
            base_score = 30
            has_weak = True
        elif min_score < MASTERY_THRESHOLD_MASTERED:
            base_score = 20
        else:
            base_score = 10
    else:
        base_score = 25  # Unstudied / no mastery recorded

    # Difficulty adjustment
    diff = (lesson.difficulty or "beginner").strip().lower()
    if diff in {"hard", "advanced"}:
        diff_adj = 10
    elif diff in {"medium", "intermediate"}:
        diff_adj = 5
    else:
        diff_adj = 0

    # Duration adjustment
    dur = lesson.estimated_minutes or DEFAULT_LESSON_MINUTES
    if dur > 45:
        dur_adj = 5
    elif dur > 30:
        dur_adj = 3
    else:
        dur_adj = 0

    total_score = base_score + diff_adj + dur_adj

    if has_weak or total_score >= 35:
        category = PRIORITY_HIGH
    elif total_score >= 20:
        category = PRIORITY_MEDIUM
    else:
        category = PRIORITY_LOW

    return total_score, category


def split_lesson_into_chunks(
    lesson: Lesson,
    priority: str,
    preferred_session_minutes: int,
) -> List[Dict[str, Any]]:
    """
    Splits a lesson's estimated duration into session units no larger than
    preferred_session_minutes.
    
    Example: 90 mins with preferred 60 mins -> [60 mins, 30 mins].
    """
    dur = lesson.estimated_minutes
    if dur is None or dur <= 0:
        dur = DEFAULT_LESSON_MINUTES

    if dur <= preferred_session_minutes:
        return [
            {
                "lesson_id": lesson.id,
                "duration": dur,
                "priority": priority,
                "type": SESSION_TYPE_LESSON,
            }
        ]

    chunks: List[Dict[str, Any]] = []
    rem = dur
    while rem > 0:
        chunk_dur = min(rem, preferred_session_minutes)
        chunks.append(
            {
                "lesson_id": lesson.id,
                "duration": chunk_dur,
                "priority": priority,
                "type": SESSION_TYPE_LESSON,
            }
        )
        rem -= chunk_dur

    return chunks


def build_revision_chunks(
    all_lessons: List[Lesson],
    mastery_by_concept: Dict[str, UserMastery],
    mastery_by_lesson_id: Dict[int, List[UserMastery]],
    allowed_revision_capacity: int,
    preferred_session_minutes: int,
) -> List[Dict[str, Any]]:
    """
    Builds revision chunks targeted at weak and developing topics without
    exceeding allowed_revision_capacity.
    
    Priority order for revision:
    1. Weak concepts (score < 60)
    2. Developing concepts (60 <= score < 80)
    3. Previously studied difficult lessons
    4. General course lessons
    """
    if allowed_revision_capacity <= 0:
        return []

    # Rank lessons for revision
    candidates: List[Tuple[int, str, Lesson]] = []
    for l in all_lessons:
        # Calculate mastery for revision ranking
        scores: List[float] = []
        if l.id in mastery_by_lesson_id:
            for m in mastery_by_lesson_id[l.id]:
                scores.append(m.mastery_score)
        if l.key_concepts and isinstance(l.key_concepts, list):
            for c in l.key_concepts:
                c_norm = normalize_concept(str(c))
                if c_norm:
                    c_key = c_norm.lower()
                    if c_key in mastery_by_concept:
                        scores.append(mastery_by_concept[c_key].mastery_score)
                    elif c_norm in mastery_by_concept:
                        scores.append(mastery_by_concept[c_norm].mastery_score)

        if scores:
            min_score = min(scores)
            if min_score < MASTERY_THRESHOLD_DEVELOPING:
                rank = 1  # Weak
                prio = PRIORITY_HIGH
            elif min_score < MASTERY_THRESHOLD_MASTERED:
                rank = 2  # Developing
                prio = PRIORITY_MEDIUM
            else:
                rank = 4  # Mastered
                prio = PRIORITY_LOW
        else:
            diff = (l.difficulty or "beginner").lower()
            if diff in {"hard", "advanced"}:
                rank = 3
                prio = PRIORITY_MEDIUM
            else:
                rank = 5
                prio = PRIORITY_LOW

        candidates.append((rank, prio, l))

    candidates.sort(key=lambda item: item[0])

    revision_chunks: List[Dict[str, Any]] = []
    allocated_rev_minutes = 0

    for rank, prio, lesson in candidates:
        if allocated_rev_minutes >= allowed_revision_capacity:
            break
        rem_rev = allowed_revision_capacity - allocated_rev_minutes
        l_dur = lesson.estimated_minutes or DEFAULT_LESSON_MINUTES
        chunk_dur = min(preferred_session_minutes, rem_rev, l_dur)
        if chunk_dur > 0:
            revision_chunks.append(
                {
                    "lesson_id": lesson.id,
                    "duration": chunk_dur,
                    "priority": prio,
                    "type": SESSION_TYPE_REVISION,
                }
            )
            allocated_rev_minutes += chunk_dur

    return revision_chunks


def allocate_sessions_to_schedule(
    dates: List[date],
    windows: List[Dict[str, str]],
    daily_limit: int,
    items_to_schedule: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Deterministically places session chunks into available calendar dates and time windows.
    
    Guarantees:
    - Never schedules outside availability windows.
    - Never overlaps sessions.
    - Never exceeds daily study limit.
    """
    sorted_windows = sorted(windows, key=lambda w: time_str_to_minutes(w["start"]))
    queue = [dict(item) for item in items_to_schedule]
    allocated: List[Dict[str, Any]] = []

    for session_date in dates:
        scheduled_today = 0

        for win in sorted_windows:
            curr_min = time_str_to_minutes(win["start"])
            end_min = time_str_to_minutes(win["end"])

            while curr_min < end_min and scheduled_today < daily_limit and queue:
                chunk = queue[0]
                needed = chunk["duration"]
                avail_win = end_min - curr_min
                avail_day = daily_limit - scheduled_today
                slot_capacity = min(avail_win, avail_day)

                if slot_capacity <= 0:
                    break

                alloc_dur = min(needed, slot_capacity)
                start_str = minutes_to_time_str(curr_min)
                end_str = minutes_to_time_str(curr_min + alloc_dur)

                allocated.append(
                    {
                        "lesson_id": chunk["lesson_id"],
                        "session_date": session_date,
                        "start_time": start_str,
                        "end_time": end_str,
                        "duration_minutes": alloc_dur,
                        "session_type": chunk["type"],
                        "status": SESSION_STATUS_SCHEDULED,
                        "priority": chunk["priority"],
                    }
                )

                curr_min += alloc_dur
                scheduled_today += alloc_dur

                if alloc_dur >= needed:
                    queue.pop(0)
                else:
                    chunk["duration"] -= alloc_dur

        if not queue:
            break

    return allocated


def generate_study_plan(
    db: Session,
    user_id: int,
    course_id: int,
    completed_lesson_ids: Optional[List[int]] = None,
    start_date: Optional[date] = None,
) -> StudyPlan:
    """
    Orchestrates deterministic study plan generation:
    1. Validates user, course, and saved preferences.
    2. Loads course lessons and user mastery data.
    3. Identifies remaining syllabus and weak concepts.
    4. Calculates available study capacity and checks deadline feasibility.
    5. Prioritizes and splits lessons into session chunks.
    6. Allocates revision capacity if workload allows.
    7. Atomically creates or updates StudyPlan and persists StudySession records.
    """
    # 1. Validate User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found.",
        )

    # 2. Validate Course
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found.",
        )

    # 3. Load Preferences
    preferences = (
        db.query(StudyPreference)
        .filter(
            StudyPreference.user_id == user_id,
            StudyPreference.course_id == course_id,
        )
        .first()
    )
    if not preferences:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Study preferences not found for user {user_id} and course {course_id}. Please configure preferences first.",
        )

    effective_start = start_date or date.today()
    if preferences.exam_date <= effective_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exam date ({preferences.exam_date}) must be after start date ({effective_start}).",
        )

    # 4. Load Course Lessons
    all_lessons = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .filter(Module.course_id == course_id)
        .order_by(Module.order_number, Lesson.order_number)
        .all()
    )
    if not all_lessons:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Course {course_id} has no lessons to schedule.",
        )

    # 5. Load User Mastery
    mastery_records = (
        db.query(UserMastery)
        .filter(UserMastery.user_id == user_id, UserMastery.course_id == course_id)
        .all()
    )
    mastery_by_concept: Dict[str, UserMastery] = {}
    mastery_by_lesson_id: Dict[int, List[UserMastery]] = {}
    for m in mastery_records:
        if m.concept:
            norm_c = normalize_concept(m.concept)
            if norm_c:
                mastery_by_concept[norm_c] = m
                mastery_by_concept[norm_c.lower()] = m
        if m.lesson_id:
            mastery_by_lesson_id.setdefault(m.lesson_id, []).append(m)

    # 6. Determine Completed & Remaining Lessons
    completed_ids = determine_completed_lessons(
        db=db,
        user_id=user_id,
        course_id=course_id,
        explicit_completed_ids=completed_lesson_ids,
    )
    remaining_lessons = [l for l in all_lessons if l.id not in completed_ids]

    # 7. Calculate Available Dates
    available_dates = calculate_available_dates(
        start_date=effective_start,
        exam_date=preferences.exam_date,
        available_days=preferences.available_days or [],
    )
    if not available_dates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No available study days found between start date and exam date matching your preferences.",
        )

    # 8. Calculate Daily & Total Available Capacity
    windows = preferences.availability_windows or []
    if not windows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No availability windows specified in study preferences.",
        )

    total_window_mins = sum(
        time_str_to_minutes(w["end"]) - time_str_to_minutes(w["start"])
        for w in windows
    )
    daily_effective_capacity = min(preferences.daily_study_limit_minutes, total_window_mins)
    total_available_capacity = len(available_dates) * daily_effective_capacity

    # 9. Calculate Remaining Syllabus Workload
    total_lesson_workload = sum(
        (l.estimated_minutes if (l.estimated_minutes and l.estimated_minutes > 0) else DEFAULT_LESSON_MINUTES)
        for l in remaining_lessons
    )

    # 10. Verify Feasibility before Exam Deadline
    if total_available_capacity < total_lesson_workload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Exam date is too soon for remaining workload. "
                f"Available capacity is {total_available_capacity} minutes across {len(available_dates)} study days, "
                f"but remaining lessons require {total_lesson_workload} minutes."
            ),
        )

    # 11. Prioritize Remaining Lessons
    prioritized_lessons: List[Tuple[int, str, Lesson]] = []
    for l in remaining_lessons:
        p_score, p_cat = calculate_lesson_priority(
            lesson=l,
            mastery_by_concept=mastery_by_concept,
            mastery_by_lesson_id=mastery_by_lesson_id,
        )
        prioritized_lessons.append((p_score, p_cat, l))

    # Sort: Higher priority score first, preserving curriculum sequence second
    prioritized_lessons.sort(key=lambda item: (-item[0], item[2].order_number))

    # 12. Split Lessons into Session Chunks
    pref_session = min(
        preferences.preferred_session_minutes or 60,
        preferences.daily_study_limit_minutes,
    )
    lesson_chunks: List[Dict[str, Any]] = []
    for p_score, p_cat, l in prioritized_lessons:
        chunks = split_lesson_into_chunks(
            lesson=l,
            priority=p_cat,
            preferred_session_minutes=pref_session,
        )
        lesson_chunks.extend(chunks)

    # 13. Revision Capacity Allocation
    surplus_capacity = total_available_capacity - total_lesson_workload
    target_revision_capacity = int(math.floor(total_available_capacity * REVISION_CAPACITY_RATIO))
    allowed_revision_capacity = min(surplus_capacity, target_revision_capacity)

    revision_chunks: List[Dict[str, Any]] = []
    if allowed_revision_capacity >= 15:
        revision_chunks = build_revision_chunks(
            all_lessons=all_lessons,
            mastery_by_concept=mastery_by_concept,
            mastery_by_lesson_id=mastery_by_lesson_id,
            allowed_revision_capacity=allowed_revision_capacity,
            preferred_session_minutes=pref_session,
        )

    # 14. Place Chunks into Schedule: Remaining Lessons First, Revision Second
    all_chunks = lesson_chunks + revision_chunks
    allocated_sessions = allocate_sessions_to_schedule(
        dates=available_dates,
        windows=windows,
        daily_limit=preferences.daily_study_limit_minutes,
        items_to_schedule=all_chunks,
    )

    # 15. Atomic Persistence & Safe Regeneration
    try:
        # Check for existing active plan
        plan = (
            db.query(StudyPlan)
            .filter(
                StudyPlan.user_id == user_id,
                StudyPlan.course_id == course_id,
                StudyPlan.status == "active",
            )
            .first()
        )

        if plan:
            plan.exam_date = preferences.exam_date
            plan.updated_at = datetime.utcnow()
            # Safely delete scheduled sessions from existing plan; preserve completed/missed history!
            db.query(StudySession).filter(
                StudySession.study_plan_id == plan.id,
                StudySession.status == SESSION_STATUS_SCHEDULED,
            ).delete()
            db.flush()
        else:
            plan = StudyPlan(
                user_id=user_id,
                course_id=course_id,
                exam_date=preferences.exam_date,
                status="active",
                total_planned_minutes=0,
            )
            db.add(plan)
            db.flush()

        # Add newly scheduled sessions
        for s_data in allocated_sessions:
            session_record = StudySession(
                study_plan_id=plan.id,
                lesson_id=s_data["lesson_id"],
                session_date=s_data["session_date"],
                start_time=s_data["start_time"],
                end_time=s_data["end_time"],
                duration_minutes=s_data["duration_minutes"],
                session_type=s_data["session_type"],
                status=s_data["status"],
                priority=s_data["priority"],
            )
            db.add(session_record)

        db.flush()

        # Compute total planned minutes for active plan
        total_mins = (
            db.query(StudySession)
            .filter(StudySession.study_plan_id == plan.id)
            .with_entities(StudySession.duration_minutes)
            .all()
        )
        plan.total_planned_minutes = sum(r[0] for r in total_mins)

        db.commit()
        db.refresh(plan)
        return plan

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.error("Failed to generate study plan: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during study plan generation: {exc}",
        ) from exc
