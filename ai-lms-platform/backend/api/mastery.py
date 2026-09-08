"""
api/mastery.py - Concept Mastery Tracking & Weak-Topic Detection Endpoints.

Provides REST APIs for:
- GET /api/mastery/user/{user_id}/course/{course_id}: Retrieves all mastery records for a student in a course.
- GET /api/mastery/user/{user_id}/course/{course_id}/weak: Retrieves weak concepts (score < 60), sorted lowest first.
- GET /api/mastery/user/{user_id}/course/{course_id}/summary: Retrieves aggregate progress metrics across concepts.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import User, Course, UserMastery
from ai.mastery import (
    MASTERY_THRESHOLD_MASTERED,
    MASTERY_THRESHOLD_DEVELOPING,
    STATUS_MASTERED,
    STATUS_DEVELOPING,
    STATUS_WEAK,
)
from .quiz_schemas import (
    MasteryResponse,
    CourseMasterySummaryResponse,
)

logger = logging.getLogger("lms.api.mastery")

router = APIRouter(prefix="/api/mastery", tags=["Mastery"])


def _validate_user_and_course(user_id: int, course_id: int, db: Session) -> tuple:
    """Helper verifying that both user and course exist; raises 404 otherwise."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning("Mastery lookup failed: User %d not found.", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found.",
        )

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        logger.warning("Mastery lookup failed: Course %d not found.", course_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID {course_id} not found.",
        )

    return user, course


@router.get(
    "/user/{user_id}/course/{course_id}",
    response_model=List[MasteryResponse],
    summary="Get student mastery records for a course",
    description="Returns all concept mastery records for the specified user and course.",
)
def get_user_course_mastery(
    user_id: int,
    course_id: int,
    db: Session = Depends(get_db),
):
    _validate_user_and_course(user_id, course_id, db)

    records = db.query(UserMastery).filter(
        UserMastery.user_id == user_id,
        UserMastery.course_id == course_id,
    ).order_by(UserMastery.concept.asc()).all()

    return [MasteryResponse.model_validate(r) for r in records]


@router.get(
    "/user/{user_id}/course/{course_id}/weak",
    response_model=List[MasteryResponse],
    summary="Get student weak concepts for a course",
    description="Returns concepts with mastery score < 60, sorted by lowest score first for targeted review.",
)
def get_user_weak_topics(
    user_id: int,
    course_id: int,
    db: Session = Depends(get_db),
):
    _validate_user_and_course(user_id, course_id, db)

    records = db.query(UserMastery).filter(
        UserMastery.user_id == user_id,
        UserMastery.course_id == course_id,
        UserMastery.mastery_score < MASTERY_THRESHOLD_DEVELOPING,
    ).order_by(UserMastery.mastery_score.asc()).all()

    return [MasteryResponse.model_validate(r) for r in records]


@router.get(
    "/user/{user_id}/course/{course_id}/summary",
    response_model=CourseMasterySummaryResponse,
    summary="Get student course mastery summary",
    description="Returns aggregate metrics: total concepts, mastered/developing/weak counts, average mastery score, and weak topics list.",
)
def get_user_course_mastery_summary(
    user_id: int,
    course_id: int,
    db: Session = Depends(get_db),
):
    _validate_user_and_course(user_id, course_id, db)

    records = db.query(UserMastery).filter(
        UserMastery.user_id == user_id,
        UserMastery.course_id == course_id,
    ).all()

    total_concepts = len(records)
    mastered_count = sum(1 for r in records if r.mastery_score >= MASTERY_THRESHOLD_MASTERED)
    developing_count = sum(
        1 for r in records if MASTERY_THRESHOLD_DEVELOPING <= r.mastery_score < MASTERY_THRESHOLD_MASTERED
    )
    weak_count = sum(1 for r in records if r.mastery_score < MASTERY_THRESHOLD_DEVELOPING)

    avg_mastery = (
        round(sum(r.mastery_score for r in records) / total_concepts, 1)
        if total_concepts > 0
        else 0.0
    )

    weak_records = sorted(
        [r for r in records if r.mastery_score < MASTERY_THRESHOLD_DEVELOPING],
        key=lambda x: x.mastery_score,
    )

    return CourseMasterySummaryResponse(
        user_id=user_id,
        course_id=course_id,
        total_concepts=total_concepts,
        mastered=mastered_count,
        developing=developing_count,
        weak=weak_count,
        average_mastery=avg_mastery,
        weak_concepts=[MasteryResponse.model_validate(w) for w in weak_records],
        mastery_records=[MasteryResponse.model_validate(r) for r in records],
        overall_mastery_score=avg_mastery,
    )
