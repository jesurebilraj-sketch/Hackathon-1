"""
api/analytics.py - Student Course Analytics & Learning Intelligence Endpoints.

Provides REST APIs for Phase 8:
- GET /api/analytics/user/{user_id}/course/{course_id}: Full student course analytics
  (course progress, quiz performance, mastery, study activity).
- GET /api/analytics/user/{user_id}/course/{course_id}/performance: Safe quiz performance history.
- GET /api/analytics/user/{user_id}/course/{course_id}/overview: Compact dashboard overview.
- GET /api/analytics/: Analytics service status.
"""

import logging
from typing import Dict, List, Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import (
    User,
    Course,
    Module,
    Lesson,
    Quiz,
    QuizSubmission,
    UserMastery,
    StudyPlan,
    StudySession,
)
from ai.mastery import (
    MASTERY_THRESHOLD_MASTERED,
    MASTERY_THRESHOLD_DEVELOPING,
)
from .analytics_schemas import (
    CourseProgressAnalytics,
    QuizPerformanceAnalytics,
    MasteryAnalytics,
    StudyActivityAnalytics,
    StudentCourseAnalyticsResponse,
    QuizPerformanceRecordResponse,
    CourseAnalyticsOverviewResponse,
)

logger = logging.getLogger("lms.api.analytics")

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


def _validate_user_and_course(user_id: int, course_id: int, db: Session) -> Tuple[User, Course]:
    """Verifies that both user and course exist; raises HTTP 404 otherwise."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning("Analytics lookup failed: User %d not found.", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found.",
        )

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        logger.warning("Analytics lookup failed: Course %d not found.", course_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID {course_id} not found.",
        )

    return user, course


def _calculate_course_analytics(
    user_id: int,
    course_id: int,
    db: Session,
) -> Tuple[CourseProgressAnalytics, QuizPerformanceAnalytics, MasteryAnalytics, StudyActivityAnalytics]:
    """
    Computes deterministic student course analytics using existing database records.
    Avoids N+1 queries by executing batched course/user-scoped queries.
    """
    # 1. Course Progress (Lessons & Modules)
    lessons = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .filter(Module.course_id == course_id)
        .all()
    )
    total_lessons = len(lessons)
    course_lesson_ids = {l.id for l in lessons}

    # 2. Study Activity (StudyPlans & StudySessions)
    sessions = (
        db.query(StudySession)
        .join(StudyPlan, StudySession.study_plan_id == StudyPlan.id)
        .filter(
            StudyPlan.user_id == user_id,
            StudyPlan.course_id == course_id,
        )
        .all()
    )

    total_planned_minutes = sum(s.duration_minutes for s in sessions)
    completed_minutes = sum(s.duration_minutes for s in sessions if s.status == "completed")
    completed_sessions = sum(1 for s in sessions if s.status == "completed")
    missed_sessions = sum(1 for s in sessions if s.status == "missed")
    scheduled_sessions = sum(1 for s in sessions if s.status == "scheduled")

    # A lesson is completed if it has a completed StudySession for this user and course
    completed_session_lesson_ids = {
        s.lesson_id
        for s in sessions
        if s.status == "completed" and s.lesson_id is not None
    }.intersection(course_lesson_ids)

    completed_lessons = len(completed_session_lesson_ids)
    completion_percentage = (
        round((completed_lessons / total_lessons) * 100.0, 1)
        if total_lessons > 0
        else 0.0
    )

    course_progress = CourseProgressAnalytics(
        total_lessons=total_lessons,
        completed_lessons=completed_lessons,
        completion_percentage=completion_percentage,
    )

    study_activity = StudyActivityAnalytics(
        total_planned_minutes=total_planned_minutes,
        completed_minutes=completed_minutes,
        completed_sessions=completed_sessions,
        missed_sessions=missed_sessions,
        scheduled_sessions=scheduled_sessions,
    )

    # 3. Quiz Performance (Submissions strictly for this course and user)
    submissions = (
        db.query(QuizSubmission)
        .join(Quiz, QuizSubmission.quiz_id == Quiz.id)
        .filter(
            QuizSubmission.user_id == user_id,
            Quiz.course_id == course_id,
        )
        .all()
    )

    quizzes_attempted = len(submissions)
    if quizzes_attempted > 0:
        percentages = [s.percentage for s in submissions]
        average_score = round(sum(percentages) / quizzes_attempted, 1)
        best_score = round(max(percentages), 1)
        passed_quizzes = sum(1 for s in submissions if s.passed)
        pass_rate = round((passed_quizzes / quizzes_attempted) * 100.0, 1)
    else:
        average_score = 0.0
        best_score = 0.0
        passed_quizzes = 0
        pass_rate = 0.0

    quiz_performance = QuizPerformanceAnalytics(
        quizzes_attempted=quizzes_attempted,
        average_score=average_score,
        best_score=best_score,
        passed_quizzes=passed_quizzes,
        pass_rate=pass_rate,
    )

    # 4. Mastery
    mastery_records = (
        db.query(UserMastery)
        .filter(
            UserMastery.user_id == user_id,
            UserMastery.course_id == course_id,
        )
        .all()
    )

    total_concepts = len(mastery_records)
    mastered_concepts = sum(1 for r in mastery_records if r.mastery_score >= MASTERY_THRESHOLD_MASTERED)
    developing_concepts = sum(
        1 for r in mastery_records if MASTERY_THRESHOLD_DEVELOPING <= r.mastery_score < MASTERY_THRESHOLD_MASTERED
    )
    weak_concepts = sum(1 for r in mastery_records if r.mastery_score < MASTERY_THRESHOLD_DEVELOPING)

    overall_mastery = (
        round(sum(r.mastery_score for r in mastery_records) / total_concepts, 1)
        if total_concepts > 0
        else 0.0
    )

    weak_sorted = sorted(
        [r for r in mastery_records if r.mastery_score < MASTERY_THRESHOLD_DEVELOPING],
        key=lambda x: x.mastery_score,
    )
    weak_topics = [r.concept for r in weak_sorted if r.concept]

    mastery = MasteryAnalytics(
        total_concepts=total_concepts,
        mastered_concepts=mastered_concepts,
        developing_concepts=developing_concepts,
        weak_concepts=weak_concepts,
        overall_mastery=overall_mastery,
        weak_topics=weak_topics,
    )

    return course_progress, quiz_performance, mastery, study_activity


@router.get("/", summary="Analytics service status")
def analytics_status():
    """Returns operational status for the Analytics API."""
    return {"status": "ready", "service": "AI-Powered LMS Analytics API"}


@router.get(
    "/user/{user_id}/course/{course_id}",
    response_model=StudentCourseAnalyticsResponse,
    summary="Get full course analytics for a student",
    description="Returns aggregate metrics covering syllabus progress, assessment results, concept mastery, and study activity.",
)
def get_student_course_analytics(
    user_id: int,
    course_id: int,
    db: Session = Depends(get_db),
):
    _validate_user_and_course(user_id, course_id, db)
    progress, quiz_perf, mastery, activity = _calculate_course_analytics(user_id, course_id, db)

    return StudentCourseAnalyticsResponse(
        user_id=user_id,
        course_id=course_id,
        course_progress=progress,
        quiz_performance=quiz_perf,
        mastery=mastery,
        study_activity=activity,
    )


@router.get(
    "/user/{user_id}/course/{course_id}/performance",
    response_model=List[QuizPerformanceRecordResponse],
    summary="Get student quiz performance history",
    description="Returns chronological quiz submission performance records without exposing internal answer keys or explanations.",
)
def get_student_quiz_performance(
    user_id: int,
    course_id: int,
    db: Session = Depends(get_db),
):
    _validate_user_and_course(user_id, course_id, db)

    submissions_with_quizzes = (
        db.query(QuizSubmission, Quiz.title)
        .join(Quiz, QuizSubmission.quiz_id == Quiz.id)
        .filter(
            QuizSubmission.user_id == user_id,
            Quiz.course_id == course_id,
        )
        .order_by(QuizSubmission.submitted_at.desc())
        .all()
    )

    results: List[QuizPerformanceRecordResponse] = []
    for sub, quiz_title in submissions_with_quizzes:
        results.append(
            QuizPerformanceRecordResponse(
                submission_id=sub.id,
                quiz_id=sub.quiz_id,
                quiz_title=quiz_title,
                score=sub.score,
                max_score=sub.max_score,
                percentage=sub.percentage,
                passed=sub.passed,
                submitted_at=sub.submitted_at,
            )
        )

    return results


@router.get(
    "/user/{user_id}/course/{course_id}/overview",
    response_model=CourseAnalyticsOverviewResponse,
    summary="Get dashboard overview analytics for a student course",
    description="Returns a high-priority summary of course progress, quiz score, mastery, study minutes, sessions, and weak topics.",
)
def get_student_course_overview(
    user_id: int,
    course_id: int,
    db: Session = Depends(get_db),
):
    _validate_user_and_course(user_id, course_id, db)
    progress, quiz_perf, mastery, activity = _calculate_course_analytics(user_id, course_id, db)

    return CourseAnalyticsOverviewResponse(
        user_id=user_id,
        course_id=course_id,
        course_progress_percentage=progress.completion_percentage,
        completion_percentage=progress.completion_percentage,
        average_quiz_score=quiz_perf.average_score,
        overall_mastery=mastery.overall_mastery,
        mastered_concepts=mastery.mastered_concepts,
        developing_concepts=mastery.developing_concepts,
        weak_concepts=mastery.weak_concepts,
        completed_study_minutes=activity.completed_minutes,
        completed_minutes=activity.completed_minutes,
        completed_sessions=activity.completed_sessions,
        missed_sessions=activity.missed_sessions,
        weak_topics=mastery.weak_topics,
    )
