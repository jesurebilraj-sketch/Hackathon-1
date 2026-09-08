"""
api/quiz_schemas.py - Pydantic Request & Response Schemas for the AI Assessment System.

Provides data schemas for:
- Quiz generation requests
- Student-facing quiz & question responses (STRICT: NEVER exposes correct_answer or explanation)
- Teacher/Detail quiz & question responses (for instructor/admin views)
- Quiz submission requests & submission results
- Itemized question feedback
- User concept mastery responses & summaries
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# 1. Quiz Generation Schemas
# ---------------------------------------------------------------------------

class QuizGenerateRequest(BaseModel):
    """Payload for initiating AI or deterministic fallback quiz generation."""
    course_id: Optional[int] = Field(None, description="Optional ID of the course the quiz belongs to")
    module_id: Optional[int] = Field(None, description="Optional module ID if scoping to a module")
    lesson_id: Optional[int] = Field(None, description="Optional lesson ID if scoping to a lesson")
    quiz_type: str = Field(
        default="lesson_quiz",
        description="Type of quiz: 'lesson_quiz', 'module_quiz', or 'course_exam'",
    )
    title: Optional[str] = Field(None, description="Optional custom title for the quiz")
    num_questions: int = Field(
        default=5,
        ge=1,
        le=30,
        description="Number of questions to generate (1 to 30)",
    )
    difficulty: str = Field(
        default="medium",
        description="Difficulty level: 'easy', 'medium', 'hard', or 'adaptive'",
    )
    time_limit_minutes: Optional[int] = Field(
        None,
        ge=1,
        description="Optional time limit in minutes",
    )
    passing_score_percentage: int = Field(
        default=70,
        ge=1,
        le=100,
        description="Minimum score percentage required to pass (1 to 100)",
    )


# ---------------------------------------------------------------------------
# 2. Student-Facing Schemas (ZERO Answer/Explanation Leakage)
# ---------------------------------------------------------------------------

class QuizQuestionStudentResponse(BaseModel):
    """
    Student-facing question schema.
    CRITICAL SECURITY REQUIREMENT:
    MUST NOT contain or expose `correct_answer` or `explanation`.
    """
    id: int = Field(..., description="Unique question identifier")
    quiz_id: int = Field(..., description="Parent quiz identifier")
    question_text: str = Field(..., description="The question prompt")
    question_type: str = Field(
        default="multiple_choice",
        description="Question type: 'multiple_choice', 'true_false', 'short_answer'",
    )
    options: List[str] = Field(
        default_factory=list,
        description="List of possible answer choices for the student",
    )
    points: int = Field(default=1, description="Points awarded for a correct answer")
    difficulty: str = Field(default="medium", description="Question difficulty")
    concept: Optional[str] = Field(None, description="Domain concept tested by this question")
    order_number: int = Field(default=1, description="Display sequence order within the quiz")

    model_config = ConfigDict(from_attributes=True)


class QuizStudentResponse(BaseModel):
    """
    Student-facing quiz presentation schema.
    Delivers the full quiz structure with questions safe for students to answer
    without exposing any answers or explanations.
    """
    id: int = Field(..., description="Quiz ID")
    title: str = Field(..., description="Quiz title")
    description: Optional[str] = Field(None, description="Quiz instructions or overview")
    course_id: int = Field(..., description="Associated course ID")
    module_id: Optional[int] = Field(None, description="Associated module ID")
    lesson_id: Optional[int] = Field(None, description="Associated lesson ID")
    quiz_type: str = Field(default="lesson_quiz", description="Type of quiz")
    passing_score_percentage: int = Field(default=70, description="Passing threshold percentage")
    time_limit_minutes: Optional[int] = Field(None, description="Time limit in minutes")
    is_fallback: bool = Field(default=False, description="Whether generated via fallback")
    created_at: datetime = Field(..., description="Creation timestamp")
    questions: List[QuizQuestionStudentResponse] = Field(
        default_factory=list,
        description="List of student-safe questions (answers and explanations omitted)",
    )

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# 3. Teacher / Detail Schemas (Includes Answers & Explanations)
# ---------------------------------------------------------------------------

class QuizQuestionDetailResponse(BaseModel):
    """
    Full question detail schema for instructors, course admins, or test validation.
    Includes correct answer and pedagogical explanation.
    """
    id: int
    quiz_id: int
    question_text: str
    question_type: str
    options: List[str]
    correct_answer: str
    explanation: str
    points: int = 1
    difficulty: str = "medium"
    concept: Optional[str] = None
    order_number: int = 1

    model_config = ConfigDict(from_attributes=True)


class QuizDetailResponse(BaseModel):
    """Full quiz detail schema with complete questions, answers, and explanations."""
    id: int
    title: str
    description: Optional[str] = None
    course_id: int
    module_id: Optional[int] = None
    lesson_id: Optional[int] = None
    quiz_type: str
    passing_score_percentage: int
    time_limit_minutes: Optional[int] = None
    is_fallback: bool
    created_at: datetime
    questions: List[QuizQuestionDetailResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# 4. Quiz Submission & Feedback Schemas
# ---------------------------------------------------------------------------

class QuizSubmissionRequest(BaseModel):
    """
    Payload submitted by a student to submit their answers for grading.
    `answers` maps question_id (as string or int key) to the student's selected answer text.
    """
    user_id: int = Field(..., description="ID of the student submitting the quiz")
    answers: Dict[str, Any] = Field(
        ...,
        description="Map of question_id -> student answer string",
    )


class QuizQuestionFeedback(BaseModel):
    """Itemized evaluation of a single question after grading."""
    question_id: int = Field(..., description="Question identifier")
    question_text: Optional[str] = Field(None, description="The original question prompt")
    user_answer: Optional[str] = Field(None, description="The answer selected by the student")
    correct_answer: str = Field(..., description="The expected correct answer")
    is_correct: bool = Field(..., description="Whether the student's answer was correct")
    points_earned: float = Field(..., description="Points awarded for this answer")
    points_possible: float = Field(..., description="Maximum points possible for this question")
    explanation: str = Field(..., description="Pedagogical explanation grounding the correct answer")
    concept: Optional[str] = Field(None, description="Associated learning concept")

    model_config = ConfigDict(from_attributes=True)


class QuizSubmissionResultResponse(BaseModel):
    """Graded quiz submission result returned to the student."""
    id: int = Field(..., description="Unique submission ID")
    quiz_id: int = Field(..., description="Quiz ID")
    user_id: int = Field(..., description="User ID of the student")
    score: float = Field(..., description="Points earned")
    max_score: float = Field(..., description="Maximum possible points")
    percentage: float = Field(..., description="Score as a percentage (0.0 - 100.0)")
    passed: bool = Field(..., description="True if percentage >= passing_score_percentage")
    answers: Dict[str, Any] = Field(default_factory=dict, description="Raw submitted answers")
    feedback: Optional[List[QuizQuestionFeedback]] = Field(
        None,
        description="Itemized question-by-question feedback with explanations",
    )
    submitted_at: datetime = Field(..., description="Timestamp of submission")

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# 5. User Mastery Schemas
# ---------------------------------------------------------------------------

class MasteryResponse(BaseModel):
    """Concept mastery state for an individual student."""
    id: int = Field(..., description="Mastery record ID")
    user_id: int = Field(..., description="User ID")
    course_id: int = Field(..., description="Course ID")
    lesson_id: Optional[int] = Field(None, description="Associated lesson ID if lesson-scoped")
    concept: Optional[str] = Field(None, description="Tested domain concept name")
    mastery_score: float = Field(..., description="Current mastery score (0.0 to 100.0)")
    attempts_count: int = Field(default=1, description="Number of assessment attempts")
    status: str = Field(
        default="needs_review",
        description="Mastery status: 'needs_review', 'learning', 'proficient', 'mastered'",
    )
    updated_at: datetime = Field(..., description="Timestamp of last mastery update")

    model_config = ConfigDict(from_attributes=True)


class CourseMasterySummaryResponse(BaseModel):
    """Aggregated mastery profile for a student across all concepts in a course."""
    user_id: int = Field(..., description="User ID")
    course_id: int = Field(..., description="Course ID")
    total_concepts: int = Field(default=0, description="Total unique concepts evaluated")
    mastered: int = Field(default=0, description="Count of concepts with score >= 80")
    developing: int = Field(default=0, description="Count of concepts with 60 <= score < 80")
    weak: int = Field(default=0, description="Count of concepts with score < 60")
    average_mastery: float = Field(default=0.0, description="Average mastery percentage across concepts")
    weak_concepts: List[MasteryResponse] = Field(
        default_factory=list,
        description="List of weak concepts (score < 60), sorted lowest score first",
    )
    overall_mastery_score: Optional[float] = Field(
        default=0.0,
        description="Legacy alias for average mastery percentage",
    )
    mastery_records: Optional[List[MasteryResponse]] = Field(
        default_factory=list,
        description="Concept-by-concept mastery breakdown",
    )

    model_config = ConfigDict(from_attributes=True)


# Backwards compatibility alias
UserMasterySummaryResponse = CourseMasterySummaryResponse
