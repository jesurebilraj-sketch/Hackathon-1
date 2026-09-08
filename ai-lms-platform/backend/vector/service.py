"""
vector/service.py - High-Level Services for Vector Indexing and Self-Healing.

Provides functions to guarantee course vector index availability and automatic self-healing
from persisted textbook PDFs.
"""

import logging
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session

from database.models import Course
from storage import resolve_source_pdf, UPLOAD_DIR
from pdf import process_pdf, PDFExtractionError
from .store import get_vector_store, VectorStore

logger = logging.getLogger("lms.vector.service")


def ensure_course_vector_index(
    course_id: int,
    db: Session,
    vector_store: Optional[VectorStore] = None,
) -> int:
    """
    Ensures that a valid vector index exists for the specified course.

    Behavior:
    1. Checks if the course already has an active vector index containing chunks.
       If so, returns immediately without re-extracting or re-embedding.
    2. If the index is missing, empty, or corrupted, inspects the course in the database.
    3. If the course has an uploaded source_file:
       - Resolves the persisted PDF path on disk.
       - Processes the PDF through the extraction pipeline.
       - Rebuilds and persists the vector index via replace_course_chunks().
    4. If the course has no source_file or the PDF is missing, safely fails without crashing.

    Args:
        course_id: The target course identifier.
        db: Active SQLAlchemy database session.
        vector_store: Optional VectorStore instance (defaults to shared singleton).

    Returns:
        int: Number of chunks available in the course index (0 if unavailable).
    """
    store = vector_store or get_vector_store()

    # 1. Fast path: index exists and is populated
    try:
        if store.has_course_index(course_id):
            count = store.count_course_chunks(course_id)
            if count > 0:
                return count
    except Exception as exc:
        logger.warning(
            "Vector store check encountered notice for course %d: %s. Attempting self-heal.",
            course_id,
            exc,
        )

    # 2. Check course source material in database
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course or not course.source_file:
        logger.info("Course %d has no source_file; cannot build vector index.", course_id)
        return 0

    # 3. Locate source PDF on disk
    resolved_name, resolved_path = resolve_source_pdf(course.source_file)
    if resolved_path and resolved_path.exists():
        source_path = resolved_path
    else:
        source_path = Path(course.source_file)
        if not source_path.is_absolute():
            source_path = UPLOAD_DIR / course.source_file

    if not source_path.exists():
        logger.warning(
            "Source PDF file '%s' for course %d not found on disk at %s. Cannot rebuild index.",
            course.source_file,
            course_id,
            source_path,
        )
        return 0

    # 4. Extract chunks and rebuild vector index
    try:
        pdf_payload = process_pdf(source_path, original_filename=course.title)
        chunks = pdf_payload.get("chunks", [])
        if not chunks:
            logger.warning("PDF extraction returned 0 chunks for course %d.", course_id)
            return 0

        indexed_count = store.replace_course_chunks(course_id=course_id, chunks=chunks)
        logger.info(
            "Self-healed and rebuilt vector index for course %d (%d chunks indexed).",
            course_id,
            indexed_count,
        )
        return indexed_count
    except PDFExtractionError as p_err:
        logger.warning("PDF extraction failed while rebuilding course %d: %s", course_id, p_err)
        return 0
    except Exception as exc:
        logger.error(
            "Unexpected error rebuilding vector index for course %d from %s: %s",
            course_id,
            source_path,
            exc,
            exc_info=True,
        )
        return 0
