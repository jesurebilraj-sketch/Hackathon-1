"""
api/analytics_schemas.py - Pydantic Schemas for LMS Analytics.

Defines response models for:
- Student course analytics (course progress, quiz performance, mastery, study activity)
- Student quiz performance history (safe records without answer keys)
- Compact dashboard overview metrics
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class CourseProgressAnalytics(BaseModel):
    """Metrics tracking student syllabus and lesson completion."""
    total_lessons: int = Field(0, description="Total number of lessons in the course")
    completed_lessons: int = Field(0, description="Number of lessons completed by the student")
    completion_percentage: float = Field(0.0, description="Course completion percentage (0.0 to 100.0)")


class QuizPerformanceAnalytics(BaseModel):
    """Metrics tracking student assessment performance."""
    quizzes_attempted: int = Field(0, description="Total number of quiz attempts for this course")
    average_score: float = Field(0.0, description="Average percentage score across all attempted quizzes")
    best_score: float = Field(0.0, description="Highest percentage score achieved across all attempted quizzes")
    passed_quizzes: int = Field(0, description="Number of quiz submissions that met or exceeded passing threshold")
    pass_rate: float = Field(0.0, description="Percentage of quiz attempts that were passed (0.0 to 100.0)")


class MasteryAnalytics(BaseModel):
    """Metrics tracking conceptual mastery and weak topics."""
    total_concepts: int = Field(0, description="Total tracked concepts for this course")
    mastered_concepts: int = Field(0, description="Concepts with mastery score >= 80%")
    developing_concepts: int = Field(0, description="Concepts with mastery score between 60% and 79%")
    weak_concepts: int = Field(0, description="Concepts with mastery score < 60%")
    overall_mastery: float = Field(0.0, description="Average mastery score across all tracked concepts")
    weak_topics: List[str] = Field(
        default_factory=list,
        description="List of concept names needing review, sorted lowest score first",
    )


class StudyActivityAnalytics(BaseModel):
    """Metrics tracking study timetable adherence and time investment."""
    total_planned_minutes: int = Field(0, description="Total study minutes planned across all sessions")
    completed_minutes: int = Field(0, description="Total study minutes in completed sessions")
    completed_sessions: int = Field(0, description="Number of completed study sessions")
    missed_sessions: int = Field(0, description="Number of missed study sessions")
    scheduled_sessions: int = Field(0, description="Number of scheduled/pending study sessions")


class StudentCourseAnalyticsResponse(BaseModel):
    """Full analytics payload for a student in a course."""
    user_id: int
    course_id: int
    course_progress: CourseProgressAnalytics
    quiz_performance: QuizPerformanceAnalytics
    mastery: MasteryAnalytics
    study_activity: StudyActivityAnalytics


class QuizPerformanceRecordResponse(BaseModel):
    """Safe student-facing quiz submission record (zero answer keys or internal explanations)."""
    submission_id: int = Field(..., description="Quiz submission record ID")
    quiz_id: int = Field(..., description="ID of the attempted quiz")
    quiz_title: Optional[str] = Field(None, description="Title of the quiz")
    score: float = Field(..., description="Points earned on the quiz")
    max_score: float = Field(..., description="Maximum possible points on the quiz")
    percentage: float = Field(..., description="Score percentage earned (0.0 to 100.0)")
    passed: bool = Field(..., description="Whether the submission met the quiz passing threshold")
    submitted_at: datetime = Field(..., description="Timestamp when the quiz was submitted")


class CourseAnalyticsOverviewResponse(BaseModel):
    """Compact dashboard-friendly analytics overview combining high-priority indicators."""
    user_id: int
    course_id: int
    course_progress_percentage: float = Field(..., description="Overall course completion percentage")
    completion_percentage: float = Field(..., description="Alias for course_progress_percentage")
    average_quiz_score: float = Field(..., description="Average quiz percentage score")
    overall_mastery: float = Field(..., description="Overall concept mastery percentage score")
    mastered_concepts: int = Field(..., description="Count of mastered concepts")
    developing_concepts: int = Field(..., description="Count of developing concepts")
    weak_concepts: int = Field(..., description="Count of weak concepts")
    completed_study_minutes: int = Field(..., description="Total completed study time in minutes")
    completed_minutes: int = Field(..., description="Alias for completed_study_minutes")
    completed_sessions: int = Field(..., description="Count of completed study sessions")
    missed_sessions: int = Field(..., description="Count of missed study sessions")
    weak_topics: List[str] = Field(default_factory=list, description="Weak topic names sorted by severity")
