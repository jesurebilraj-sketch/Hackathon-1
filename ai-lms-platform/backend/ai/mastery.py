"""
ai/mastery.py - Deterministic Concept Mastery Tracking & Weak-Topic Detection.

Provides mathematical, deterministic calculations for student concept mastery:
- Normalizes concept strings to prevent duplication from whitespace or case differences.
- Aggregates per-question points earned vs possible for each concept.
- Computes updated mastery using a weighted cumulative running average across attempts.
- Classifies status deterministically:
    - mastery_score >= 80.0 -> 'mastered'
    - mastery_score >= 60.0 -> 'developing'
    - mastery_score < 60.0  -> 'weak'
- Manages atomic UserMastery record updates within an active SQLAlchemy session.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from database.models import UserMastery

logger = logging.getLogger("lms.ai.mastery")

# ---------------------------------------------------------------------------
# Centralized Status Threshold Constants
# ---------------------------------------------------------------------------
MASTERY_THRESHOLD_MASTERED = 80.0
MASTERY_THRESHOLD_DEVELOPING = 60.0

STATUS_MASTERED = "mastered"
STATUS_DEVELOPING = "developing"
STATUS_WEAK = "weak"


def classify_mastery_status(score: float) -> str:
    """
    Deterministically classifies a 0-100 mastery score into a progress status.

    Thresholds:
    - score >= 80.0 -> 'mastered'
    - score >= 60.0 -> 'developing'
    - score < 60.0  -> 'weak'
    """
    if score >= MASTERY_THRESHOLD_MASTERED:
        return STATUS_MASTERED
    elif score >= MASTERY_THRESHOLD_DEVELOPING:
        return STATUS_DEVELOPING
    else:
        return STATUS_WEAK


def normalize_concept(raw_concept: Optional[str]) -> Optional[str]:
    """
    Normalizes a concept string by stripping whitespace.
    Returns None if the concept is None or empty.
    """
    if not raw_concept:
        return None
    cleaned = raw_concept.strip()
    return cleaned if cleaned else None


def calculate_concept_performance(feedback_items: List[Any]) -> Dict[str, Dict[str, Any]]:
    """
    Aggregates question feedback items by concept.

    For each question:
    - If concept is missing or empty, it is skipped.
    - Questions with identical concepts (case/space-insensitive) are grouped together.
    - Concept score = (earned_points / possible_points) * 100.0.

    Returns a dict keyed by lowercase normalized concept:
    {
        "binary search": {
            "canonical_concept": "Binary Search",
            "earned_points": 4.0,
            "possible_points": 5.0,
            "current_score": 80.0,
        }
    }
    """
    concept_map: Dict[str, Dict[str, Any]] = {}

    for item in feedback_items:
        # Extract concept string from Pydantic model or dict
        if isinstance(item, dict):
            raw_concept = item.get("concept")
            points_earned = float(item.get("points_earned", 0.0))
            points_possible = float(item.get("points_possible", 1.0))
        else:
            raw_concept = getattr(item, "concept", None)
            points_earned = float(getattr(item, "points_earned", 0.0))
            points_possible = float(getattr(item, "points_possible", 1.0))

        canonical = normalize_concept(raw_concept)
        if not canonical:
            # Skip questions without concept tags
            continue

        key = canonical.lower()
        if key not in concept_map:
            concept_map[key] = {
                "canonical_concept": canonical,
                "earned_points": 0.0,
                "possible_points": 0.0,
                "current_score": 0.0,
            }

        concept_map[key]["earned_points"] += points_earned
        concept_map[key]["possible_points"] += points_possible

    for data in concept_map.values():
        possible = data["possible_points"]
        earned = data["earned_points"]
        data["current_score"] = round((earned / possible) * 100.0, 2) if possible > 0 else 0.0

    return concept_map


def calculate_updated_mastery(
    previous_score: Optional[float],
    previous_attempts: int,
    current_score: float,
) -> Tuple[float, int, str]:
    """
    Calculates updated mastery score and status using a cumulative running average.

    Formula:
    - First attempt (previous_attempts == 0 or previous_score is None):
        new_mastery = current_score
        attempts_count = 1
    - Subsequent attempts (previous_attempts >= 1):
        new_mastery = ((previous_score * previous_attempts) + current_score) / (previous_attempts + 1)
        attempts_count = previous_attempts + 1

    Returns:
        (new_mastery_score, new_attempts_count, new_status)
    """
    if previous_score is None or previous_attempts <= 0:
        new_score = round(float(current_score), 2)
        new_attempts = 1
    else:
        new_attempts = previous_attempts + 1
        new_score = round(
            ((previous_score * previous_attempts) + current_score) / new_attempts,
            2,
        )

    # Clamp bounds strictly to [0.0, 100.0]
    new_score = max(0.0, min(100.0, new_score))
    new_status = classify_mastery_status(new_score)

    return new_score, new_attempts, new_status


def update_user_mastery_for_submission(
    db: Session,
    user_id: int,
    course_id: int,
    lesson_id: Optional[int],
    feedback_items: List[Any],
) -> List[UserMastery]:
    """
    Aggregates concept performance from quiz feedback and updates/creates UserMastery
    records in the active session.

    Ensures:
    - Zero duplicate records for the same (user_id, course_id, concept).
    - Attempts count increments deterministically.
    - Updated mastery score is calculated via weighted average.
    - Associated with lesson_id if quiz was lesson-scoped.
    - Changes are flushed to the active session; caller handles final atomic commit or rollback.
    """
    concept_perf = calculate_concept_performance(feedback_items)
    if not concept_perf:
        logger.info("No concept-tagged questions found in submission; skipping mastery update.")
        return []

    # Fetch all existing mastery records for this user and course to perform deterministic lookup
    existing_records = db.query(UserMastery).filter(
        UserMastery.user_id == user_id,
        UserMastery.course_id == course_id,
    ).all()

    # Index by lowercase normalized concept
    existing_map: Dict[str, UserMastery] = {}
    for r in existing_records:
        if r.concept:
            existing_map[r.concept.strip().lower()] = r

    updated_records: List[UserMastery] = []

    for concept_key, data in concept_perf.items():
        canonical_name = data["canonical_concept"]
        current_score = data["current_score"]

        if concept_key in existing_map:
            record = existing_map[concept_key]
            new_score, new_attempts, new_status = calculate_updated_mastery(
                previous_score=record.mastery_score,
                previous_attempts=record.attempts_count,
                current_score=current_score,
            )
            record.mastery_score = new_score
            record.attempts_count = new_attempts
            record.status = new_status
            record.updated_at = datetime.utcnow()
            if lesson_id is not None:
                record.lesson_id = lesson_id
            logger.info(
                "Updated UserMastery: user=%d course=%d concept='%s' -> score=%.1f%% status='%s' attempts=%d",
                user_id, course_id, canonical_name, new_score, new_status, new_attempts,
            )
        else:
            new_score, new_attempts, new_status = calculate_updated_mastery(
                previous_score=None,
                previous_attempts=0,
                current_score=current_score,
            )
            record = UserMastery(
                user_id=user_id,
                course_id=course_id,
                lesson_id=lesson_id,
                concept=canonical_name,
                mastery_score=new_score,
                attempts_count=new_attempts,
                status=new_status,
                updated_at=datetime.utcnow(),
            )
            db.add(record)
            existing_map[concept_key] = record
            logger.info(
                "Created UserMastery: user=%d course=%d concept='%s' -> score=%.1f%% status='%s' attempts=%d",
                user_id, course_id, canonical_name, new_score, new_status, new_attempts,
            )

        updated_records.append(record)

    db.flush()
    return updated_records
