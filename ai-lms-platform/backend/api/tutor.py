"""
api/tutor.py - FastAPI Endpoints for the AI Academic Tutor & Knowledge Base.

Routes:
- POST /api/tutor/course/{course_id}/ask: Submits student question, performs grounded RAG retrieval,
  enforces refusal guardrails, returns structured response with textbook citations.
- GET /api/tutor/course/{course_id}/context: Retrieves relevant indexed context chunks for a query
  with strict course isolation for debugging and inspection.
- GET /api/tutor/: Health and readiness check for tutor service.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import Course
from ai.tutor import ask_tutor, extract_chunk_excerpt
from vector import get_vector_store, ensure_course_vector_index
from .tutor_schemas import (
    TutorQueryRequest,
    TutorQueryResponse,
    SourceCitation,
    TutorContextResponse,
)

logger = logging.getLogger("lms.api.tutor")

router = APIRouter(prefix="/api/tutor", tags=["AI Tutor"])


@router.get("/", summary="AI Tutor service status")
def tutor_status():
    """Health/readiness check for the AI Tutor and Knowledge Base service."""
    return {
        "status": "ready",
        "service": "AI Tutor & Grounded RAG Knowledge Base",
        "version": "1.0.0",
    }


@router.post(
    "/course/{course_id}/ask",
    response_model=TutorQueryResponse,
    summary="Ask the AI Tutor a course-grounded question",
)
def ask_course_tutor(
    course_id: int,
    payload: TutorQueryRequest,
    db: Session = Depends(get_db),
):
    """
    Submits a student question to the grounded AI academic tutor for a specific course.

    - Validates course existence (404).
    - Validates course source material exists (400).
    - Validates question text (400/422).
    - Retrieves top-k semantically relevant chunks strictly from course_id vector index.
    - Applies conservative out-of-scope refusal guardrails.
    - Generates grounded answer with source citations.
    - Falls back to deterministic synthesis when LLM is unavailable or in test mode.
    """
    # 1. Validate course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID {course_id} not found.",
        )

    # 2. Validate course has source material
    if not course.source_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Course {course_id} does not have source material or an uploaded PDF textbook.",
        )

    # 3. Validate question is non-blank
    clean_question = payload.question.strip() if payload.question else ""
    if not clean_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty or blank whitespace.",
        )

    # 4. Self-heal/ensure course vector index exists
    ensure_course_vector_index(course_id=course_id, db=db)

    # 5. Invoke AI Tutor service
    try:
        tutor_resp = ask_tutor(
            course_id=course_id,
            question=clean_question,
            top_k=payload.effective_top_k,
            min_score=payload.effective_min_score,
        )

        return TutorQueryResponse(
            answer=tutor_resp.answer,
            citations=[
                SourceCitation(
                    chunk_id=c.chunk_id,
                    page_start=c.page_start,
                    page_end=c.page_end,
                    section=c.section,
                    excerpt=c.excerpt,
                    score=c.score,
                )
                for c in tutor_resp.citations
            ],
            course_id=tutor_resp.course_id,
            question=tutor_resp.question,
            is_fallback=tutor_resp.is_fallback,
            is_refusal=tutor_resp.is_refusal,
            confidence=tutor_resp.confidence,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Error handling tutor query for course %s: %s",
            course_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the tutor request.",
        )


@router.get(
    "/course/{course_id}/context",
    response_model=TutorContextResponse,
    summary="Retrieve relevant indexed course context for debugging or inspection",
)
def get_course_tutor_context(
    course_id: int,
    q: str = Query(..., min_length=1, max_length=2000, description="Search query"),
    top_k: int = Query(default=3, ge=1, le=10, description="Maximum number of context chunks"),
    min_score: float = Query(default=0.0, ge=0.0, le=1.0, description="Minimum similarity threshold"),
    db: Session = Depends(get_db),
):
    """
    Retrieves the most semantically relevant indexed chunks for a query strictly
    within the specified course. Used for debugging, inspection, and verification.
    """
    # 1. Validate course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID {course_id} not found.",
        )

    # 2. Validate course has source material
    if not course.source_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Course {course_id} does not have source material or an uploaded PDF textbook.",
        )

    # 3. Validate query
    clean_q = q.strip()
    if not clean_q:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'q' cannot be empty or blank whitespace.",
        )

    # 4. Self-heal/ensure course vector index exists
    ensure_course_vector_index(course_id=course_id, db=db)

    # 5. Search course-partitioned vector store
    try:
        store = get_vector_store()
        search_results = store.search(
            query=clean_q,
            course_id=course_id,
            top_k=top_k,
            min_score=min_score,
        )

        citations = [
            SourceCitation(
                chunk_id=r.chunk_id,
                page_start=r.page_start,
                page_end=r.page_end,
                section=r.section,
                excerpt=extract_chunk_excerpt(r.text),
                score=r.score,
            )
            for r in search_results
        ]

        return TutorContextResponse(
            course_id=course_id,
            query=clean_q,
            chunks_count=len(citations),
            chunks=citations,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Error retrieving context for course %s: %s",
            course_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving course context.",
        )
