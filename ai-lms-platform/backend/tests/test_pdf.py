import io
import sys
from pathlib import Path
try:
    import pymupdf as fitz
except ImportError:
    import fitz  # type: ignore
import pytest
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app
from pdf.extractor import extract_pdf, PDFExtractionError
from pdf.cleaner import clean_text, repair_hyphenation, detect_headings_from_blocks
from pdf.chunker import chunk_pages
from pdf import process_pdf

client = TestClient(app)


def create_in_memory_pdf(pages_content: list[tuple[str, float]]) -> bytes:
    """
    Creates an in-memory PDF with specified texts and font sizes per page.
    pages_content: list of (text, font_size) tuples.
    """
    doc = fitz.open()
    for text, font_size in pages_content:
        page = doc.new_page()
        page.insert_text((50, 72), text, fontsize=font_size)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# 1. Valid PDF upload test
def test_valid_pdf_upload():
    """Verify POST /api/courses/upload processes valid PDF and returns structured response."""
    page_1 = "CHAPTER 1: Introduction to Computer Systems\n\nA computer system consists of hardware and software components."
    page_2 = "1.1 Operating Systems Overview\n\nThe operating system manages CPU scheduling, memory, and file systems."
    pdf_bytes = create_in_memory_pdf([(page_1, 12.0), (page_2, 12.0)])

    response = client.post(
        "/api/courses/upload",
        files={"file": ("operating_systems.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["filename"] == "operating_systems.pdf"
    assert data["stored_filename"].endswith(".pdf")
    assert data["pages"] == 2
    assert data["characters"] > 0
    assert data["words"] > 0
    assert data["chunks"] >= 1
    assert data["processing_time"] >= 0


# 2. Invalid file type test
def test_invalid_file_type():
    """Verify non-PDF file upload is rejected with 400 Bad Request."""
    text_content = b"This is a plain text file, not a PDF."
    response = client.post(
        "/api/courses/upload",
        files={"file": ("notes.txt", io.BytesIO(text_content), "text/plain")},
    )
    assert response.status_code == 400
    assert "Invalid file format" in response.json()["detail"]


# 3. Empty file upload test
def test_empty_file_upload():
    """Verify empty 0-byte file is rejected with 400 Bad Request."""
    response = client.post(
        "/api/courses/upload",
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


# 4. Corrupted PDF handling
def test_corrupted_pdf_handling():
    """Verify corrupted file with PDF extension is rejected with 400 Bad Request."""
    corrupted_bytes = b"NotARealPDFHeader1234567890"
    response = client.post(
        "/api/courses/upload",
        files={"file": ("corrupt.pdf", io.BytesIO(corrupted_bytes), "application/pdf")},
    )
    assert response.status_code == 400
    assert "Corrupted or invalid PDF" in response.json()["detail"]


# 5. PDF with no extractable text
def test_pdf_with_no_text(tmp_path):
    """Verify blank PDF with no extractable text returns 422 Unprocessable Entity."""
    doc = fitz.open()
    doc.new_page()  # Blank page without text
    blank_pdf_bytes = doc.tobytes()
    doc.close()

    response = client.post(
        "/api/courses/upload",
        files={"file": ("blank.pdf", io.BytesIO(blank_pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 422
    assert "no extractable text" in response.json()["detail"].lower()


# 6. PDF text extraction & metadata
def test_pdf_text_extraction(tmp_path):
    """Verify extractor extracts text and accurate document statistics."""
    p1 = "First page content with ten simple words in this sentence."
    p2 = "Second page content with different words for testing extraction."
    pdf_bytes = create_in_memory_pdf([(p1, 11.0), (p2, 11.0)])

    pdf_file = tmp_path / "test_extract.pdf"
    pdf_file.write_bytes(pdf_bytes)

    result = extract_pdf(pdf_file)
    meta = result["metadata"]
    assert meta["page_count"] == 2
    assert meta["total_words"] > 0
    assert len(result["pages"]) == 2
    assert "First page" in result["pages"][0]["text"]
    assert "Second page" in result["pages"][1]["text"]


# 7. Page number preservation
def test_page_number_preservation(tmp_path):
    """Verify extracted pages maintain strict 1-indexed page numbers."""
    pages = [(f"Text for page {i}", 11.0) for i in range(1, 4)]
    pdf_bytes = create_in_memory_pdf(pages)

    pdf_file = tmp_path / "test_pages.pdf"
    pdf_file.write_bytes(pdf_bytes)

    result = extract_pdf(pdf_file)
    for idx, page_data in enumerate(result["pages"], start=1):
        assert page_data["page_number"] == idx


# 8. Text cleaning and hyphen repair
def test_text_cleaning():
    """Verify deterministic cleaning repairs hyphenation, line breaks, and whitespace."""
    raw_input = (
        "Artificial intelli-\ngence is a rapidly growing field of computer\n"
        "science .\n\n"
        "12\n\n"
        "Deep learn-\ning models achieve state-of-the-art results   in vision ."
    )
    cleaned = clean_text(raw_input, page_number=12)

    # Hyphen repairs
    assert "intelligence" in cleaned
    assert "intelli-" not in cleaned
    assert "learning" in cleaned
    assert "learn-" not in cleaned

    # Punctuation spacing cleaned
    assert "science." in cleaned
    assert "vision." in cleaned

    # Isolated page number removed
    lines = [l.strip() for l in cleaned.split("\n")]
    assert "12" not in lines


# 9. Chunk generation and limits
def test_chunk_generation():
    """Verify chunker builds chunks respecting target word limits without tiny fragments."""
    # Generate 1500 words of dummy educational text across 3 pages
    dummy_paragraph = "This is a recurring educational sentence explaining database architecture concepts. " * 15
    pages = [
        {"page_number": 1, "text": f"CHAPTER 1: Databases\n\n{dummy_paragraph}\n\n{dummy_paragraph}"},
        {"page_number": 2, "text": f"1.1 Relational Engines\n\n{dummy_paragraph}\n\n{dummy_paragraph}"},
        {"page_number": 3, "text": f"1.2 Indexing\n\n{dummy_paragraph}"},
    ]

    headings = [
        {"page_number": 1, "text": "CHAPTER 1: Databases", "level": 1},
        {"page_number": 2, "text": "1.1 Relational Engines", "level": 2},
        {"page_number": 3, "text": "1.2 Indexing", "level": 2},
    ]

    chunks = chunk_pages(pages, headings=headings, target_words=400, max_words=600, overlap_words=50, min_words=50)

    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk["word_count"] > 50
        assert chunk["character_count"] > 0
        assert chunk["chunk_id"].startswith("chunk_")
        assert chunk["section"] in ["CHAPTER 1: Databases", "1.1 Relational Engines", "1.2 Indexing"]


# 10. Chunk page citation metadata
def test_chunk_page_metadata():
    """Verify chunks accurately preserve page_start and page_end for citations."""
    pages = [
        {"page_number": 3, "text": "Start of topic on page three with several sentences of content."},
        {"page_number": 4, "text": "Continuation of topic onto page four with concluding explanations."},
    ]

    chunks = chunk_pages(pages, target_words=1000, max_words=1500, min_words=10)
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk["page_start"] == 3
    assert chunk["page_end"] == 4


# 11. Slide Layout Artifact Separation
def test_slide_layout_artifact_separation():
    """Verify that short, unpunctuated slide layout items (like numbers or headings) are not merged."""
    raw_input = (
        "Dummy line 1\n"
        "Dummy line 2\n"
        "Dummy line 3\n"
        "Our Objectives\n"
        "What we aim to achieve in this session.\n"
        "02\n"
        "03\n"
        "Raise awareness\n"
        "Promote open dialogue\n"
        "Dummy line 4\n"
        "Dummy line 5\n"
        "Dummy line 6\n"
    )
    cleaned = clean_text(raw_input, page_number=1)
    # The short, unpunctuated elements should be preserved as separate lines, not merged
    assert "Our Objectives\nWhat we aim to achieve in this session." in cleaned or "Our Objectives" in cleaned.split("\n")
    assert "02\n03\nRaise awareness\nPromote open dialogue" in cleaned

# 12. Soft Wrap Preservation
def test_soft_wrap_preservation():
    """Verify that normal short sentences ending with punctuation or hyphenated wraps merge properly."""
    raw_input = (
        "This is a normal paragraph line that is\n"
        "wrapped to the next line without any punctuation\n"
        "but it keeps going and ends here.\n\n"
        "Another short sentence.\n"
        "It ends here."
    )
    cleaned = clean_text(raw_input, page_number=1)
    assert "This is a normal paragraph line that is wrapped to the next line without any punctuation but it keeps going and ends here." in cleaned
    assert "Another short sentence. It ends here." in cleaned
