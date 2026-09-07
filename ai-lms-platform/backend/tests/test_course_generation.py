import io
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

try:
    import pymupdf as fitz
except ImportError:
    import fitz  # type: ignore

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import app
from database.database import SessionLocal
from database.models import Course, Module, Lesson, User
from ai.course_generator import (
    LessonStructure,
    ModuleStructure,
    CourseStructure,
    generate_course_from_chunks,
    group_chunks_by_section,
    CourseGenerationError,
)

client = TestClient(app)

UPLOAD_DIR = backend_dir / "storage" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def create_sample_pdf_bytes() -> bytes:
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((50, 72), "CHAPTER 1: Computer Architecture\n\nComputers execute machine instructions stored in memory.")
    p2 = doc.new_page()
    p2.insert_text((50, 72), "1.1 Memory Hierarchy\n\nCaches provide fast access to frequently referenced instructions and data.")
    p3 = doc.new_page()
    p3.insert_text((50, 72), "CHAPTER 2: Operating Systems\n\nAn operating system provides an abstraction layer over hardware devices.")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# 1. Valid AI structured output test
def test_valid_ai_structured_output():
    """Verify CourseStructure successfully validates conforming dictionary."""
    valid_data = {
        "title": "Introduction to Computer Science",
        "description": "Comprehensive introductory course covering computer architecture and operating systems.",
        "modules": [
            {
                "title": "Module 1: Architecture",
                "description": "Overview of memory and CPU design.",
                "order_number": 1,
                "lessons": [
                    {
                        "title": "Lesson 1: Memory Hierarchy",
                        "description": "Explains registers, caches, and main memory.",
                        "learning_objective": "Students will understand memory speed tradeoffs.",
                        "content": "Detailed instructional text explaining CPU caching principles.",
                        "order_number": 1,
                        "estimated_minutes": 25,
                        "difficulty": "beginner",
                        "source_pages": [1, 2],
                    }
                ],
            }
        ],
    }

    course = CourseStructure.model_validate(valid_data)
    assert course.title == "Introduction to Computer Science"
    assert len(course.modules) == 1
    assert len(course.modules[0].lessons) == 1
    assert course.modules[0].lessons[0].source_pages == [1, 2]
    assert course.modules[0].lessons[0].estimated_minutes == 25


# 2. Malformed AI output test
def test_malformed_ai_output():
    """Verify CourseStructure strictly rejects invalid or malformed output."""
    # Missing required modules field
    with pytest.raises(ValidationError):
        CourseStructure.model_validate({"title": "Incomplete Course", "description": "Too short description"})

    # Invalid empty modules list
    with pytest.raises(ValidationError):
        CourseStructure.model_validate({
            "title": "Empty Course",
            "description": "A course with a sufficiently long description but no modules.",
            "modules": [],
        })

    # Invalid lesson difficulty
    with pytest.raises(ValidationError):
        CourseStructure.model_validate({
            "title": "Invalid Lesson",
            "description": "A course description that is long enough.",
            "modules": [
                {
                    "title": "Module",
                    "description": "Module description",
                    "order_number": 1,
                    "lessons": [
                        {
                            "title": "Lesson",
                            "description": "Lesson description",
                            "learning_objective": "Objective",
                            "content": "Sufficient content string for lesson.",
                            "order_number": 1,
                            "difficulty": "extreme_impossible",  # Invalid enum value
                            "source_pages": [1],
                        }
                    ],
                }
            ],
        })


# 3. Course generation end-to-end endpoint test
def test_course_generation_endpoint():
    """Verify POST /api/courses/{course_id}/generate generates full curriculum."""
    pdf_bytes = create_sample_pdf_bytes()
    filename = "test_phase3_course.pdf"
    file_path = UPLOAD_DIR / filename
    file_path.write_bytes(pdf_bytes)

    # Create Course in DB
    create_res = client.post(
        "/api/courses/",
        json={
            "title": "Architecture & Systems",
            "description": "Initial draft course",
            "source_file": filename,
        },
    )
    assert create_res.status_code == 201
    course_id = create_res.json()["id"]

    # Trigger generation
    gen_res = client.post(f"/api/courses/{course_id}/generate")
    assert gen_res.status_code == 200
    gen_data = gen_res.json()

    assert "title" in gen_data
    assert "description" in gen_data
    assert "modules" in gen_data
    assert len(gen_data["modules"]) >= 1


# 4. Module creation in DB test
def test_module_creation_in_db():
    """Verify Module records are persisted to database linked to course."""
    pdf_bytes = create_sample_pdf_bytes()
    filename = "test_phase3_modules.pdf"
    file_path = UPLOAD_DIR / filename
    file_path.write_bytes(pdf_bytes)

    create_res = client.post(
        "/api/courses/",
        json={"title": "Systems Engineering", "source_file": filename},
    )
    course_id = create_res.json()["id"]

    gen_res = client.post(f"/api/courses/{course_id}/generate")
    assert gen_res.status_code == 200

    # Query details endpoint
    details_res = client.get(f"/api/courses/{course_id}")
    assert details_res.status_code == 200
    course_details = details_res.json()

    assert len(course_details["modules"]) >= 1
    for mod in course_details["modules"]:
        assert "id" in mod
        assert "title" in mod
        assert mod["order_number"] >= 1
        assert len(mod["lessons"]) >= 1


# 5. Lesson creation in DB test
def test_lesson_creation_in_db():
    """Verify Lesson records include estimated_minutes, difficulty, learning_objective."""
    pdf_bytes = create_sample_pdf_bytes()
    filename = "test_phase3_lessons.pdf"
    file_path = UPLOAD_DIR / filename
    file_path.write_bytes(pdf_bytes)

    create_res = client.post(
        "/api/courses/",
        json={"title": "Advanced OS", "source_file": filename},
    )
    course_id = create_res.json()["id"]

    client.post(f"/api/courses/{course_id}/generate")

    details_res = client.get(f"/api/courses/{course_id}")
    first_lesson = details_res.json()["modules"][0]["lessons"][0]

    assert "title" in first_lesson
    assert "content" in first_lesson
    assert "learning_objective" in first_lesson
    assert first_lesson["estimated_minutes"] is not None
    assert first_lesson["difficulty"] in ["beginner", "intermediate", "advanced"]


# 6. Source page preservation test
def test_source_page_preservation():
    """Verify source_pages are preserved from chunk pages."""
    pdf_bytes = create_sample_pdf_bytes()
    filename = "test_phase3_citations.pdf"
    file_path = UPLOAD_DIR / filename
    file_path.write_bytes(pdf_bytes)

    create_res = client.post(
        "/api/courses/",
        json={"title": "Source Page Citations Test", "source_file": filename},
    )
    course_id = create_res.json()["id"]

    gen_res = client.post(f"/api/courses/{course_id}/generate")
    assert gen_res.status_code == 200
    course_data = gen_res.json()

    all_source_pages = []
    for m in course_data["modules"]:
        for les in m["lessons"]:
            all_source_pages.extend(les.get("source_pages", []))

    assert len(all_source_pages) > 0
    # The source pages must be within the 3 pages of the test PDF
    for p in all_source_pages:
        assert p in [1, 2, 3]


# 7. Nonexistent course generation test
def test_nonexistent_course_generate():
    """Verify generation against invalid course ID returns 404."""
    response = client.post("/api/courses/999999/generate")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# 8. Generation failure for missing PDF file test
def test_generation_failure_missing_pdf():
    """Verify course without source_file returns 400 on generation."""
    create_res = client.post(
        "/api/courses/",
        json={"title": "Ghost Course"},
    )
    assert create_res.status_code == 201
    course_id = create_res.json()["id"]

    response = client.post(f"/api/courses/{course_id}/generate")
    assert response.status_code == 400
    assert "source pdf" in response.json()["detail"].lower()


# 9. Chunk batching large document scalability test
def test_chunk_batching_large_document():
    """Verify scalable batching partitions large documents (>50 chunks) into sub-batches."""
    dummy_chunks = [
        {
            "chunk_id": f"chunk_{i:03d}",
            "section": f"Chapter {(i // 10) + 1}",
            "page_start": i + 1,
            "page_end": i + 1,
            "text": f"Educational content for chunk {i} discussing software architecture.",
        }
        for i in range(50)
    ]

    batches = group_chunks_by_section(dummy_chunks, max_chunks_per_batch=4)
    assert len(batches) > 10  # 50 chunks split into batches of <= 4

    for b in batches:
        assert len(b["chunks"]) <= 4
        assert len(b["pages"]) >= 1
        assert "section_title" in b


# 10. Upload -> Document ID -> Course Creation -> Generation integration test
def test_upload_create_course_with_document_id_and_generate():
    """Verify full workflow: upload PDF -> create course with document_id -> generate curriculum."""
    pdf_bytes = create_sample_pdf_bytes()
    original_name = "Haressment_NV.pdf"

    # Step a: Upload PDF
    up_res = client.post(
        "/api/courses/upload",
        files={"file": (original_name, io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert up_res.status_code == 200
    up_data = up_res.json()
    doc_id = up_data["document_id"]
    stored_name = up_data["stored_filename"]
    assert doc_id in stored_name

    # Step b & c: Create course using document_id and verify resolution
    course_res = client.post(
        "/api/courses/",
        json={
            "title": "Workplace Conduct & Policy",
            "description": "Comprehensive course on workplace guidelines.",
            "document_id": doc_id,
        },
    )
    assert course_res.status_code == 201
    course_data = course_res.json()
    assert course_data["source_file"] == stored_name  # Correctly resolved to stored UUID filename!
    course_id = course_data["id"]

    # Step d: Generate course successfully
    gen_res = client.post(f"/api/courses/{course_id}/generate")
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    assert "modules" in gen_data
    assert len(gen_data["modules"]) >= 1


# 11. Create course using original filename resolution test
def test_create_course_with_original_filename_resolution():
    """Verify course created with original filename resolves to stored UUID filename."""
    pdf_bytes = create_sample_pdf_bytes()
    original_name = "Employee_Handbook.pdf"

    up_res = client.post(
        "/api/courses/upload",
        files={"file": (original_name, io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert up_res.status_code == 200
    stored_name = up_res.json()["stored_filename"]

    # Create course with original filename
    course_res = client.post(
        "/api/courses/",
        json={
            "title": "Handbook Orientation",
            "source_file": original_name,
        },
    )
    assert course_res.status_code == 201
    assert course_res.json()["source_file"] == stored_name

    course_id = course_res.json()["id"]
    gen_res = client.post(f"/api/courses/{course_id}/generate")
    assert gen_res.status_code == 200


# 12. Invalid document_id rejection test
def test_create_course_invalid_document_id():
    """Verify creating a course with a nonexistent document_id returns 400 Bad Request."""
    res = client.post(
        "/api/courses/",
        json={
            "title": "Failed Course",
            "document_id": "nonexistent-doc-id-00000",
        },
    )
    assert res.status_code == 400
    assert "not found in storage" in res.json()["detail"].lower()


# 13. Existing source_file behavior retained test
def test_create_course_existing_source_file_behavior():
    """Verify backward compatibility: creating course directly with stored filename still works."""
    pdf_bytes = create_sample_pdf_bytes()
    filename = "legacy_test_file.pdf"
    (UPLOAD_DIR / filename).write_bytes(pdf_bytes)

    res = client.post(
        "/api/courses/",
        json={
            "title": "Legacy Course Creation",
            "source_file": filename,
        },
    )
    assert res.status_code == 201
    assert res.json()["source_file"] == filename


# 14. Course generation idempotency test
def test_repeated_course_generation_is_idempotent():
    """Verify calling POST /api/courses/{course_id}/generate multiple times replaces curriculum and does not duplicate modules or lessons."""
    pdf_bytes = create_sample_pdf_bytes()
    filename = "Idempotency_Test_Doc.pdf"

    up_res = client.post(
        "/api/courses/upload",
        files={"file": (filename, io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert up_res.status_code == 200
    doc_id = up_res.json()["document_id"]

    course_res = client.post(
        "/api/courses/",
        json={"title": "Idempotent Curriculum Course", "document_id": doc_id},
    )
    assert course_res.status_code == 201
    course_id = course_res.json()["id"]

    # First generation
    gen1_res = client.post(f"/api/courses/{course_id}/generate")
    assert gen1_res.status_code == 200
    gen1_data = gen1_res.json()
    expected_module_count = len(gen1_data["modules"])
    expected_lesson_count = sum(len(m["lessons"]) for m in gen1_data["modules"])
    assert expected_module_count > 0
    assert expected_lesson_count > 0

    db = SessionLocal()
    mods_run1 = db.query(Module).filter(Module.course_id == course_id).all()
    mod_ids_run1 = [m.id for m in mods_run1]
    lessons_run1 = db.query(Lesson).filter(Lesson.module_id.in_(mod_ids_run1)).all()
    assert len(mods_run1) == expected_module_count
    assert len(lessons_run1) == expected_lesson_count
    db.close()

    # Second generation on the exact same course
    gen2_res = client.post(f"/api/courses/{course_id}/generate")
    assert gen2_res.status_code == 200
    gen2_data = gen2_res.json()

    db = SessionLocal()
    mods_run2 = db.query(Module).filter(Module.course_id == course_id).all()
    mod_ids_run2 = [m.id for m in mods_run2]
    lessons_run2 = db.query(Lesson).filter(Lesson.module_id.in_(mod_ids_run2)).all()

    # Verify no duplicate modules and no accumulated/duplicate lessons
    assert len(mods_run2) == len(gen2_data["modules"])
    assert len(lessons_run2) == sum(len(m["lessons"]) for m in gen2_data["modules"])

    # Verify old orphaned lessons do not exist for the course
    if mod_ids_run1 != mod_ids_run2:
        orphaned_lessons = db.query(Lesson).filter(Lesson.module_id.in_(mod_ids_run1)).all()
        assert len(orphaned_lessons) == 0

    db.close()


