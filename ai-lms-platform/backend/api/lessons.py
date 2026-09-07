import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import Lesson, Module, Course
from storage import resolve_source_pdf, UPLOAD_DIR
from pdf import process_pdf, PDFExtractionError
from ai.lesson_generator import (
    LessonContent,
    PracticeQuestion,
    generate_lesson_content,
    LessonGenerationError,
)

logger = logging.getLogger("lms.api.lessons")

router = APIRouter(prefix="/api/lessons", tags=["Lessons"])


# --- Response Schemas ---

class PracticeQuestionResponse(BaseModel):
    question: str = Field(..., description="The practice question")
    answer: str = Field(..., description="The correct answer")
    explanation: str = Field(..., description="Explanation grounding the answer")


class LessonContentResponse(BaseModel):
    lesson_id: int = Field(..., description="Lesson ID")
    title: str = Field(..., description="Lesson title")
    module_id: int = Field(..., description="Parent module ID")
    course_id: int = Field(..., description="Associated course ID")
    introduction: str = Field(..., description="Introduction and conceptual overview")
    explanation: str = Field(..., description="Comprehensive explanatory content")
    learning_objectives: List[str] = Field(default_factory=list, description="Measurable learning objectives")
    key_concepts: List[str] = Field(default_factory=list, description="Key domain concepts")
    examples: List[str] = Field(default_factory=list, description="Practical illustrative examples")
    key_takeaways: List[str] = Field(default_factory=list, description="Core takeaways")
    common_misconceptions: List[str] = Field(default_factory=list, description="Common mistakes and misconceptions")
    practice_questions: List[PracticeQuestionResponse] = Field(default_factory=list, description="Short practice questions")
    estimated_minutes: int = Field(default=20, description="Estimated study time in minutes")
    difficulty: str = Field(default="beginner", description="Difficulty level")
    source_pages: List[int] = Field(default_factory=list, description="Preserved source PDF page citations")
    is_fallback: bool = Field(default=False, description="Whether generated via deterministic offline fallback")


class LessonSummaryItem(BaseModel):
    id: int
    module_id: int
    title: str
    summary: Optional[str] = None
    learning_objective: Optional[str] = None
    order_number: int
    estimated_minutes: Optional[int] = 20
    difficulty: Optional[str] = "beginner"
    source_pages: Optional[List[int]] = None
    has_generated_content: bool = False


class LessonListResponse(BaseModel):
    count: int
    lessons: List[LessonSummaryItem]


# --- Endpoints ---

@router.get("/", response_model=LessonListResponse, summary="List all lessons")
def list_lessons(module_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Lesson)
    if module_id is not None:
        query = query.filter(Lesson.module_id == module_id)
    lessons = query.order_by(Lesson.order_number).all()

    items = []
    for l in lessons:
        has_content = bool(
            l.key_concepts
            or l.practice_questions
            or (l.learning_objectives and len(l.learning_objectives) > 0)
        )
        items.append(
            LessonSummaryItem(
                id=l.id,
                module_id=l.module_id,
                title=l.title,
                summary=l.summary,
                learning_objective=l.learning_objective,
                order_number=l.order_number,
                estimated_minutes=l.estimated_minutes or 20,
                difficulty=l.difficulty or "beginner",
                source_pages=l.source_pages or [],
                has_generated_content=has_content,
            )
        )

    return LessonListResponse(count=len(items), lessons=items)


@router.get("/{lesson_id}", summary="Get lesson details")
def get_lesson(lesson_id: int, db: Session = Depends(get_db)):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lesson with id {lesson_id} not found.",
        )
    has_content = bool(
        lesson.key_concepts
        or lesson.practice_questions
        or (lesson.learning_objectives and len(lesson.learning_objectives) > 0)
    )
    return {
        "id": lesson.id,
        "module_id": lesson.module_id,
        "course_id": lesson.module.course_id if lesson.module else None,
        "title": lesson.title,
        "summary": lesson.summary,
        "learning_objective": lesson.learning_objective,
        "order_number": lesson.order_number,
        "estimated_minutes": lesson.estimated_minutes,
        "difficulty": lesson.difficulty,
        "source_pages": lesson.source_pages or [],
        "has_generated_content": has_content,
    }


@router.post(
    "/{lesson_id}/generate",
    response_model=LessonContentResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate educational lesson content grounded in source PDF",
    description="Extracts source chunks associated with the lesson, invokes AI content generator, and saves structured content to the database.",
)
def generate_lesson(lesson_id: int, db: Session = Depends(get_db)):
    # 1. Verify lesson exists
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lesson with id {lesson_id} not found.",
        )

    # 2. Verify parent module and course
    module = lesson.module
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module for lesson {lesson_id} not found.",
        )

    course = module.course
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course for module {module.id} not found.",
        )

    # 3. Locate source PDF on disk
    if not course.source_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Course {course.id} does not have an uploaded source PDF.",
        )

    resolved_name, resolved_path = resolve_source_pdf(course.source_file)
    if resolved_path and resolved_path.exists():
        source_path = resolved_path
    else:
        source_path = Path(course.source_file)
        if not source_path.is_absolute():
            source_path = UPLOAD_DIR / course.source_file

    if not source_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source PDF file '{course.source_file}' was not found in storage.",
        )

    # 4. Extract chunks using Phase 2 PDF pipeline
    try:
        pdf_payload = process_pdf(source_path, original_filename=course.title)
    except PDFExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process source PDF: {exc}",
        ) from exc
    except Exception as exc:
        logger.error("Error processing PDF for lesson %d: %s", lesson_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error occurred while reading source PDF.",
        ) from exc

    chunks = pdf_payload.get("chunks", [])
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Source PDF has no extractable content chunks.",
        )

    # 5. Identify relevant grounded chunks for this lesson
    target_pages = set(lesson.source_pages or [])
    relevant_chunks = []
    if target_pages:
        for ch in chunks:
            ch_pstart = ch.get("page_start", 1)
            ch_pend = ch.get("page_end", ch_pstart)
            if set(range(ch_pstart, ch_pend + 1)) & target_pages:
                relevant_chunks.append(ch)

    # If no chunk matched by explicit pages, match by section or title keyword
    if not relevant_chunks:
        title_lower = lesson.title.lower()
        mod_title_lower = module.title.lower()
        for ch in chunks:
            sec_lower = (ch.get("section") or "").lower()
            if sec_lower in title_lower or sec_lower in mod_title_lower or title_lower in sec_lower:
                relevant_chunks.append(ch)

    # Fallback to initial slice if still no match
    if not relevant_chunks:
        relevant_chunks = chunks[:4]

    # 6. Generate rich lesson content
    try:
        content_result: LessonContent = generate_lesson_content(
            lesson_title=lesson.title,
            module_title=module.title,
            course_title=course.title,
            chunks=relevant_chunks,
            estimated_minutes=lesson.estimated_minutes or 20,
            difficulty=lesson.difficulty or "beginner",
            fallback_pages=lesson.source_pages,
        )
    except LessonGenerationError as exc:
        logger.error("Lesson generation failed for lesson %d: %s", lesson_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lesson generation failed: {exc}",
        ) from exc
    except Exception as exc:
        logger.error("Unhandled error generating lesson %d: %s", lesson_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating lesson content.",
        ) from exc

    # 7. Persist to database (in-place update for safe regeneration)
    try:
        lesson.content = content_result.explanation
        lesson.summary = content_result.introduction
        if content_result.learning_objectives:
            lesson.learning_objective = "; ".join(content_result.learning_objectives)
        lesson.learning_objectives = content_result.learning_objectives
        lesson.key_concepts = content_result.key_concepts
        lesson.examples = content_result.examples
        lesson.key_takeaways = content_result.key_takeaways
        lesson.misconceptions = content_result.common_misconceptions
        lesson.practice_questions = [q.model_dump() for q in content_result.practice_questions]
        lesson.estimated_minutes = content_result.estimated_minutes
        lesson.difficulty = content_result.difficulty
        lesson.source_pages = content_result.source_pages

        db.commit()
        db.refresh(lesson)
    except Exception as exc:
        db.rollback()
        logger.error("Failed to save lesson content for lesson %d: %s", lesson_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist generated lesson content.",
        ) from exc

    return LessonContentResponse(
        lesson_id=lesson.id,
        title=lesson.title,
        module_id=lesson.module_id,
        course_id=course.id,
        introduction=content_result.introduction,
        explanation=content_result.explanation,
        learning_objectives=content_result.learning_objectives,
        key_concepts=content_result.key_concepts,
        examples=content_result.examples,
        key_takeaways=content_result.key_takeaways,
        common_misconceptions=content_result.common_misconceptions,
        practice_questions=[
            PracticeQuestionResponse(question=q.question, answer=q.answer, explanation=q.explanation)
            for q in content_result.practice_questions
        ],
        estimated_minutes=content_result.estimated_minutes,
        difficulty=content_result.difficulty,
        source_pages=content_result.source_pages,
        is_fallback=content_result.is_fallback,
    )


@router.get(
    "/{lesson_id}/content",
    response_model=LessonContentResponse,
    summary="Get generated educational lesson content",
    description="Returns the rich educational lesson content generated by AI, including explanation, key concepts, examples, practice questions, and page citations.",
)
def get_lesson_content(lesson_id: int, db: Session = Depends(get_db)):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lesson with id {lesson_id} not found.",
        )

    # Check if content has been generated
    has_generated = bool(
        lesson.key_concepts
        or lesson.practice_questions
        or (lesson.learning_objectives and len(lesson.learning_objectives) > 0)
    )
    if not has_generated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content has not been generated for lesson {lesson_id} yet. Please call POST /api/lessons/{lesson_id}/generate first.",
        )

    course_id = lesson.module.course_id if lesson.module else 0

    practice_qs = []
    if isinstance(lesson.practice_questions, list):
        for q in lesson.practice_questions:
            if isinstance(q, dict):
                practice_qs.append(
                    PracticeQuestionResponse(
                        question=q.get("question", ""),
                        answer=q.get("answer", ""),
                        explanation=q.get("explanation", ""),
                    )
                )

    learning_objs = lesson.learning_objectives or []
    if not learning_objs and lesson.learning_objective:
        learning_objs = [lesson.learning_objective]

    return LessonContentResponse(
        lesson_id=lesson.id,
        title=lesson.title,
        module_id=lesson.module_id,
        course_id=course_id,
        introduction=lesson.summary or f"Overview of {lesson.title}",
        explanation=lesson.content or f"Comprehensive lesson content for {lesson.title}.",
        learning_objectives=learning_objs,
        key_concepts=lesson.key_concepts or [],
        examples=lesson.examples or [],
        key_takeaways=lesson.key_takeaways or [],
        common_misconceptions=lesson.misconceptions or [],
        practice_questions=practice_qs,
        estimated_minutes=lesson.estimated_minutes or 20,
        difficulty=lesson.difficulty or "beginner",
        source_pages=lesson.source_pages or [],
        is_fallback=False,
    )
