import logging
from pathlib import Path
from typing import Any, Dict, List

try:
    import pymupdf as fitz
except ImportError:
    import fitz  # type: ignore

logger = logging.getLogger("lms.pdf.extractor")


class PDFExtractionError(Exception):
    """Raised when a PDF cannot be opened, read, or parsed."""
    pass


def extract_pdf(pdf_path: str | Path) -> Dict[str, Any]:
    """
    Extracts text and page-level layout metadata from a PDF file using PyMuPDF.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        A dictionary containing:
            - "metadata": Document level stats (page_count, total_characters, total_words, empty_pages)
            - "pages": List of dicts, each with page_number, text, and text_blocks (with font metadata)
    """
    path_obj = Path(pdf_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    if path_obj.stat().st_size == 0:
        raise PDFExtractionError(f"PDF file is empty (0 bytes): {path_obj.name}")

    try:
        doc = fitz.open(str(path_obj))
    except Exception as exc:
        raise PDFExtractionError(f"Failed to open or parse PDF '{path_obj.name}': {exc}") from exc

    try:
        if doc.is_encrypted:
            raise PDFExtractionError(f"PDF '{path_obj.name}' is password protected and cannot be read.")

        page_count = len(doc)
        if page_count == 0:
            raise PDFExtractionError(f"PDF '{path_obj.name}' contains no pages.")

        pages: List[Dict[str, Any]] = []
        total_characters = 0
        total_words = 0
        empty_pages: List[int] = []

        for page_idx in range(page_count):
            page_num = page_idx + 1
            page = doc[page_idx]

            raw_text = page.get_text("text") or ""
            char_count = len(raw_text.strip())
            word_count = len(raw_text.split())

            if char_count == 0:
                empty_pages.append(page_num)

            total_characters += char_count
            total_words += word_count

            # Extract detailed block and span layout info (font size, lines) for structure detection
            page_dict = page.get_text("dict")
            blocks: List[Dict[str, Any]] = []

            for block in page_dict.get("blocks", []):
                # block type 0 is text
                if block.get("type") == 0:
                    block_text_lines = []
                    max_font_size = 0.0
                    for line in block.get("lines", []):
                        line_text = ""
                        for span in line.get("spans", []):
                            line_text += span.get("text", "")
                            span_size = span.get("size", 0.0)
                            if span_size > max_font_size:
                                max_font_size = span_size
                        if line_text.strip():
                            block_text_lines.append(line_text.strip())

                    combined_block_text = " ".join(block_text_lines).strip()
                    if combined_block_text:
                        blocks.append({
                            "text": combined_block_text,
                            "bbox": block.get("bbox"),
                            "max_font_size": round(max_font_size, 2),
                        })

            pages.append({
                "page_number": page_num,
                "text": raw_text,
                "character_count": char_count,
                "word_count": word_count,
                "blocks": blocks,
            })

        return {
            "metadata": {
                "filename": path_obj.name,
                "page_count": page_count,
                "total_characters": total_characters,
                "total_words": total_words,
                "empty_pages": empty_pages,
            },
            "pages": pages,
        }

    finally:
        doc.close()
