import logging
from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import User, Course, StudyPreference, StudyPlan, StudySession
from api.planner_schemas import (
    StudyPreferenceRequest,
    StudyPreferenceResponse,
    PlanGenerateRequest,
    StudyPlanResponse,
    StudySessionResponse,
    SessionStatusUpdate,
)
from ai.study_planner import generate_study_plan

logger = logging.getLogger("lms.api.planner")

router = APIRouter(prefix="/api/planner", tags=["Study Planner"])


def _verify_user_and_course(db: Session, user_id: int, course_id: int):
    """Helper to verify that user and course exist in the database."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found.",
        )
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found.",
        )


@router.put(
    "/user/{user_id}/course/{course_id}/preferences",
    response_model=StudyPreferenceResponse,
    summary="Create or update student study preferences",
)
def set_study_preferences(
    user_id: int,
    course_id: int,
    payload: StudyPreferenceRequest,
    db: Session = Depends(get_db),
):
    _verify_user_and_course(db, user_id, course_id)

    pref = (
        db.query(StudyPreference)
        .filter(
            StudyPreference.user_id == user_id,
            StudyPreference.course_id == course_id,
        )
        .first()
    )

    windows_data = [w.model_dump() for w in payload.availability_windows]

    if pref:
        pref.exam_date = payload.exam_date
        pref.daily_study_limit_minutes = payload.daily_study_limit_minutes
        pref.available_days = payload.available_days
        pref.availability_windows = windows_data
        pref.preferred_session_minutes = payload.preferred_session_minutes
        pref.updated_at = datetime.utcnow()
    else:
        pref = StudyPreference(
            user_id=user_id,
            course_id=course_id,
            exam_date=payload.exam_date,
            daily_study_limit_minutes=payload.daily_study_limit_minutes,
            available_days=payload.available_days,
            availability_windows=windows_data,
            preferred_session_minutes=payload.preferred_session_minutes,
        )
        db.add(pref)

    try:
        db.commit()
        db.refresh(pref)
    except Exception as exc:
        db.rollback()
        logger.error("Failed to save study preferences: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save study preferences.",
        ) from exc

    return pref


@router.get(
    "/user/{user_id}/course/{course_id}/preferences",
    response_model=StudyPreferenceResponse,
    summary="Get student study preferences for a course",
)
def get_study_preferences(
    user_id: int,
    course_id: int,
    db: Session = Depends(get_db),
):
    _verify_user_and_course(db, user_id, course_id)

    pref = (
        db.query(StudyPreference)
        .filter(
            StudyPreference.user_id == user_id,
            StudyPreference.course_id == course_id,
        )
        .first()
    )
    if not pref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study preferences not found for user {user_id} and course {course_id}.",
        )
    return pref


@router.post(
    "/user/{user_id}/course/{course_id}/generate",
    response_model=StudyPlanResponse,
    summary="Generate a personalized study timetable idempotently",
)
def generate_plan_endpoint(
    user_id: int,
    course_id: int,
    payload: Optional[PlanGenerateRequest] = None,
    db: Session = Depends(get_db),
):
    _verify_user_and_course(db, user_id, course_id)

    completed_ids = payload.completed_lesson_ids if payload else None
    start_dt = payload.start_date if payload else None

    plan = generate_study_plan(
        db=db,
        user_id=user_id,
        course_id=course_id,
        completed_lesson_ids=completed_ids,
        start_date=start_dt,
    )
    return plan


@router.get(
    "/user/{user_id}/course/{course_id}",
    response_model=StudyPlanResponse,
    summary="Get active study plan and sessions for a student",
)
def get_study_plan(
    user_id: int,
    course_id: int,
    db: Session = Depends(get_db),
):
    _verify_user_and_course(db, user_id, course_id)

    plan = (
        db.query(StudyPlan)
        .filter(
            StudyPlan.user_id == user_id,
            StudyPlan.course_id == course_id,
            StudyPlan.status == "active",
        )
        .first()
    )
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active study plan found for user {user_id} and course {course_id}.",
        )
    return plan


@router.get(
    "/user/{user_id}/course/{course_id}/today",
    response_model=List[StudySessionResponse],
    summary="Get study sessions scheduled for today",
)
def get_today_sessions(
    user_id: int,
    course_id: int,
    db: Session = Depends(get_db),
):
    _verify_user_and_course(db, user_id, course_id)

    plan = (
        db.query(StudyPlan)
        .filter(
            StudyPlan.user_id == user_id,
            StudyPlan.course_id == course_id,
            StudyPlan.status == "active",
        )
        .first()
    )
    if not plan:
        return []

    today_dt = date.today()
    sessions = (
        db.query(StudySession)
        .filter(
            StudySession.study_plan_id == plan.id,
            StudySession.session_date == today_dt,
        )
        .order_by(StudySession.start_time)
        .all()
    )
    return sessions


@router.get(
    "/user/{user_id}/course/{course_id}/upcoming",
    response_model=List[StudySessionResponse],
    summary="Get upcoming study sessions sorted chronologically",
)
def get_upcoming_sessions(
    user_id: int,
    course_id: int,
    db: Session = Depends(get_db),
):
    _verify_user_and_course(db, user_id, course_id)

    plan = (
        db.query(StudyPlan)
        .filter(
            StudyPlan.user_id == user_id,
            StudyPlan.course_id == course_id,
            StudyPlan.status == "active",
        )
        .first()
    )
    if not plan:
        return []

    today_dt = date.today()
    sessions = (
        db.query(StudySession)
        .filter(
            StudySession.study_plan_id == plan.id,
            StudySession.session_date >= today_dt,
        )
        .order_by(StudySession.session_date, StudySession.start_time)
        .all()
    )
    return sessions


@router.patch(
    "/sessions/{session_id}",
    response_model=StudySessionResponse,
    summary="Update a study session status (e.g. completed or missed)",
)
def update_session_status(
    session_id: int,
    payload: SessionStatusUpdate,
    db: Session = Depends(get_db),
):
    session_record = db.query(StudySession).filter(StudySession.id == session_id).first()
    if not session_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study session with id {session_id} not found.",
        )

    session_record.status = payload.status
    try:
        db.commit()
        db.refresh(session_record)
    except Exception as exc:
        db.rollback()
        logger.error("Failed to update session %d: %s", session_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update session status.",
        ) from exc

    return session_record
