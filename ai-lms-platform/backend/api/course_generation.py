import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import Course, Module, Lesson
from pdf import process_pdf, PDFExtractionError
from storage import resolve_source_pdf, UPLOAD_DIR
from ai.course_generator import (
    generate_course_from_chunks,
    CourseStructure,
    CourseGenerationError,
)

logger = logging.getLogger("lms.api.generation")

router = APIRouter(prefix="/api/courses", tags=["Course Generation"])


@router.post(
    "/{course_id}/generate",
    response_model=CourseStructure,
    status_code=status.HTTP_200_OK,
    summary="Generate course curriculum from uploaded PDF",
    description="Processes the course's uploaded PDF, chunks the content, invokes AI course generator, and creates modules and lessons.",
)
def generate_course_curriculum(course_id: int, db: Session = Depends(get_db)):
    # 1. Verify course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found.",
        )

    # 2. Verify course has an uploaded source PDF
    if not course.source_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Course {course_id} does not have an uploaded source PDF. Please upload a PDF first.",
        )

    # 3. Locate source PDF on disk (resolves document_id, original filename, or stored filename)
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

    # 4. Process PDF using Phase 2 pipeline
    try:
        pdf_payload = process_pdf(source_path, original_filename=course.title)
    except PDFExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process source PDF: {exc}",
        ) from exc
    except Exception as exc:
        logger.error("Error running PDF processing for course %d: %s", course_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error occurred while processing PDF content.",
        ) from exc

    chunks = pdf_payload.get("chunks", [])
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Source PDF has no extractable content chunks to generate a course.",
        )

    # 5. Generate structured course via AI course generator
    try:
        course_structure = generate_course_from_chunks(chunks, course_title=course.title)
    except CourseGenerationError as exc:
        logger.error("AI course generation failed for course %d: %s", course_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Course generation failed: {exc}",
        ) from exc
    except Exception as exc:
        logger.error("Unhandled error during course generation for course %d: %s", course_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the structured curriculum.",
        ) from exc

    # 6. Atomically persist modules and lessons in the database
    try:
        # Clear existing modules/lessons if regenerating
        db.query(Module).filter(Module.course_id == course.id).delete()
        db.flush()

        # Update course description if provided
        if course_structure.description:
            course.description = course_structure.description

        for mod_data in course_structure.modules:
            new_module = Module(
                course_id=course.id,
                title=mod_data.title,
                description=mod_data.description,
                order_number=mod_data.order_number,
            )
            db.add(new_module)
            db.flush()  # Populates new_module.id

            for les_data in mod_data.lessons:
                new_lesson = Lesson(
                    module_id=new_module.id,
                    title=les_data.title,
                    summary=les_data.description,
                    learning_objective=les_data.learning_objective,
                    content=les_data.content,
                    order_number=les_data.order_number,
                    estimated_minutes=les_data.estimated_minutes,
                    difficulty=les_data.difficulty,
                    source_pages=les_data.source_pages,
                )
                db.add(new_lesson)

        db.commit()
        db.refresh(course)
    except Exception as exc:
        db.rollback()
        logger.error("Failed to persist generated course to database: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save generated curriculum to database.",
        ) from exc

    return course_structure
