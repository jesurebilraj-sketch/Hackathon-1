"""
api/tutor_schemas.py - Pydantic Request & Response Schemas for the AI Tutor & Knowledge Base.

Provides data schemas for:
- Student question query requests with retrieval parameters (top_k, min_score)
- Grounded source citations from textbook chunks
- Structured AI tutor responses with citations, confidence, and refusal/fallback indicators
- Context inspection & debugging responses partitioned strictly by course
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


class SourceCitation(BaseModel):
    """Citation metadata identifying where information was found in course material."""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    page_start: int = Field(..., description="Source PDF starting page number")
    page_end: int = Field(..., description="Source PDF ending page number")
    section: str = Field(..., description="Chapter or section heading")
    excerpt: str = Field(..., description="Short relevant text excerpt from the chunk")
    score: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")

    model_config = ConfigDict(from_attributes=True)


class TutorQueryRequest(BaseModel):
    """Request payload for student asking a question to the course AI tutor."""
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The student's academic question about the course material",
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of context chunks to retrieve (1 to 10)",
    )
    min_score: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity threshold (0.0 to 1.0)",
    )
    similarity_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional alias for min_score threshold (0.0 to 1.0)",
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Question cannot be empty or blank whitespace.")
        return cleaned

    @property
    def effective_min_score(self) -> float:
        """Returns similarity_threshold if specified, otherwise min_score."""
        if self.similarity_threshold is not None:
            return self.similarity_threshold
        return self.min_score

    @property
    def effective_top_k(self) -> int:
        """Returns validated top_k."""
        return self.top_k


class TutorQueryResponse(BaseModel):
    """Structured response from the AI tutor with citations and grounding flags."""
    answer: str = Field(..., description="Educational explanation or refusal message")
    citations: List[SourceCitation] = Field(
        default_factory=list,
        description="Source textbook references cited in the answer",
    )
    course_id: int = Field(..., description="Course identifier")
    question: str = Field(..., description="The student's submitted question")
    is_fallback: bool = Field(
        default=False,
        description="Whether generated via deterministic offline fallback",
    )
    is_refusal: bool = Field(
        default=False,
        description="Whether query was refused as out-of-scope or unsupported",
    )
    confidence: float = Field(
        default=0.0,
        description="Highest retrieval similarity score (0.0 to 1.0)",
    )

    model_config = ConfigDict(from_attributes=True)


class TutorContextResponse(BaseModel):
    """Context inspection & debugging response showing indexed chunks for a query."""
    course_id: int = Field(..., description="Course identifier")
    query: str = Field(..., description="Search query used for context retrieval")
    chunks_count: int = Field(..., description="Total relevant chunks retrieved")
    chunks: List[SourceCitation] = Field(
        default_factory=list,
        description="Relevant context chunks strictly from this course",
    )

    model_config = ConfigDict(from_attributes=True)
