import time
from pathlib import Path
from typing import Any, Dict, Optional

from .extractor import extract_pdf, PDFExtractionError
from .cleaner import clean_text, detect_headings_from_blocks
from .chunker import chunk_pages

__all__ = [
    "extract_pdf",
    "clean_text",
    "detect_headings_from_blocks",
    "chunk_pages",
    "process_pdf",
    "PDFExtractionError",
]


def process_pdf(file_path: str | Path, original_filename: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes the complete PDF processing pipeline:
    1. Extract pages, text, and layout metadata using PyMuPDF.
    2. Clean extracted text deterministically per page.
    3. Detect structural headings and sections.
    4. Intelligently chunk the document with page citations and section headers.

    Args:
        file_path: Path to the stored PDF file.
        original_filename: Optional original user-uploaded filename.

    Returns:
        Structured document payload containing metadata, cleaned pages, sections, and chunks.
    """
    start_time = time.perf_counter()
    path_obj = Path(file_path)

    # 1. Extraction
    extraction_result = extract_pdf(path_obj)
    raw_pages = extraction_result["pages"]

    # 2. Structure / Heading Detection
    headings = detect_headings_from_blocks(raw_pages)

    # 3. Deterministic Text Cleaning
    cleaned_pages = []
    total_cleaned_characters = 0
    total_cleaned_words = 0

    for p in raw_pages:
        p_num = p["page_number"]
        cleaned_text = clean_text(p["text"], page_number=p_num)
        c_count = len(cleaned_text)
        w_count = len(cleaned_text.split())
        total_cleaned_characters += c_count
        total_cleaned_words += w_count

        cleaned_pages.append({
            "page_number": p_num,
            "text": cleaned_text,
            "character_count": c_count,
            "word_count": w_count,
        })

    # 4. Intelligent Chunking
    chunks = chunk_pages(cleaned_pages, headings=headings)

    elapsed = time.perf_counter() - start_time

    return {
        "metadata": {
            "filename": original_filename or path_obj.name,
            "stored_filename": path_obj.name,
            "pages": extraction_result["metadata"]["page_count"],
            "characters": total_cleaned_characters,
            "words": total_cleaned_words,
            "empty_pages": extraction_result["metadata"]["empty_pages"],
            "chunks": len(chunks),
            "sections_detected": len(headings),
            "processing_time": round(elapsed, 3),
        },
        "pages": cleaned_pages,
        "sections": headings,
        "chunks": chunks,
    }
