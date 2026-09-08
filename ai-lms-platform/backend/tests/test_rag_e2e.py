"""
tests/test_rag_e2e.py - Phase 6 Step 4 End-to-End RAG Pipeline Integration Tests.

Verifies the complete automated pipeline without manual vector seeding:
1. Upload real educational PDF via POST /api/courses/upload.
2. Create course referencing document_id via POST /api/courses/.
3. Generate course curriculum via POST /api/courses/{course_id}/generate.
4. Verify curriculum generation automatically builds vector index for the course.
5. Query AI Tutor via POST /api/tutor/course/{course_id}/ask:
   - Returns HTTP 200
   - Non-empty grounded answer
   - Non-empty citations strictly from the uploaded PDF
   - Citation metadata (page numbers, section, excerpt)
6. Self-Healing Verification:
   - Corrupt/delete the course vector index from memory and disk.
   - Query the AI Tutor again.
   - Confirm ensure_course_vector_index automatically rebuilds the vector index from the stored PDF.
7. Strict Cross-Course Isolation:
   - Course B cannot retrieve chunks or citations from Course A.
"""

import io
import os
from pathlib import Path
from unittest.mock import patch
import pytest

try:
    import pymupdf as fitz
except ImportError:
    import fitz  # type: ignore

from database.models import User, Course
from ai.course_generator import CourseStructure, ModuleStructure, LessonStructure
from vector import get_vector_store


def create_quantum_pdf_bytes() -> bytes:
    """Generates a test PDF with distinct sections on quantum computing."""
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text(
        (50, 72),
        "CHAPTER 1: Quantum Computing Foundations\n\n"
        "Quantum bits or qubits can exist in superpositions of state zero and state one simultaneously. "
        "This property allows quantum computers to evaluate vast computational spaces.",
    )
    p2 = doc.new_page()
    p2.insert_text(
        (50, 72),
        "1.2 Quantum Entanglement\n\n"
        "Entangled pairs of particles display instantaneous correlation regardless of spatial separation. "
        "Bell state measurements verify non-local quantum mechanics.",
    )
    p3 = doc.new_page()
    p3.insert_text(
        (50, 72),
        "CHAPTER 2: Quantum Algorithms\n\n"
        "Shor's algorithm provides exponential speedup for integer factorization over classical computers. "
        "Grover's algorithm achieves quadratic speedup for unstructured database search.",
    )
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_economics_pdf_bytes() -> bytes:
    """Generates a second distinct test PDF for cross-course isolation testing."""
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text(
        (50, 72),
        "CHAPTER 1: Principles of Microeconomics\n\n"
        "Supply and demand determine equilibrium prices in competitive markets. "
        "Elasticity measures consumer responsiveness to price changes.",
    )
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def mock_quantum_curriculum() -> CourseStructure:
    return CourseStructure(
        title="Quantum Computing Foundations",
        description="Comprehensive introduction to quantum computing and algorithms.",
        modules=[
            ModuleStructure(
                title="Module 1: Fundamentals",
                description="Qubits and entanglement.",
                order_number=1,
                lessons=[
                    LessonStructure(
                        title="Lesson 1: Superposition & Entanglement",
                        description="Learn qubit states.",
                        learning_objective="Understand superposition.",
                        content="Detailed lesson content on quantum mechanics.",
                        order_number=1,
                        estimated_minutes=25,
                        difficulty="beginner",
                        source_pages=[1, 2],
                    )
                ],
            )
        ],
    )


def test_full_rag_pipeline_upload_to_tutor_and_self_healing(client):
    """
    End-to-end integration test:
    Upload PDF -> Create Course -> Generate Curriculum -> Automatic Indexing -> Ask Tutor -> Self-Healing
    """
    pdf_bytes = create_quantum_pdf_bytes()
    filename = "quantum_computing_handbook.pdf"

    # 1. Upload PDF
    upload_res = client.post(
        "/api/courses/upload",
        files={"file": (filename, io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    doc_id = upload_res.json()["document_id"]
    assert doc_id is not None

    # 2. Create Course referencing document_id
    create_res = client.post(
        "/api/courses/",
        json={
            "title": "Quantum Computing Foundations",
            "document_id": doc_id,
            "description": "Intro to quantum mechanics",
        },
    )
    assert create_res.status_code == 201, f"Course creation failed: {create_res.text}"
    course_id = create_res.json()["id"]

    # 3. Generate Curriculum (which triggers auto-indexing)
    with patch.dict(os.environ, {"TEST_MODE": "true"}), patch(
        "api.course_generation.generate_course_from_chunks",
        return_value=mock_quantum_curriculum(),
    ):
        gen_res = client.post(f"/api/courses/{course_id}/generate")
        assert gen_res.status_code == 200, f"Generation failed: {gen_res.text}"

    # 4. Confirm Vector Store was automatically indexed WITHOUT manual seeding
    store = get_vector_store()
    assert store.has_course_index(course_id), "Vector index was not automatically created!"
    chunk_count = store.count_course_chunks(course_id)
    assert chunk_count >= 1, f"Expected at least 1 chunk indexed, got {chunk_count}"

    # 5. Query Tutor via POST /api/tutor/course/{course_id}/ask
    with patch.dict(os.environ, {"TEST_MODE": "true"}):
        tutor_res = client.post(
            f"/api/tutor/course/{course_id}/ask",
            json={
                "question": "What is quantum entanglement and how do particles behave?",
                "min_score": 0.10,
            },
        )
        assert tutor_res.status_code == 200, f"Tutor query failed: {tutor_res.text}"
        data = tutor_res.json()

        # Assert response schema and contents
        assert data["course_id"] == course_id
        assert data["is_refusal"] is False
        assert len(data["answer"]) > 0
        assert len(data["citations"]) >= 1

        citation = data["citations"][0]
        assert citation["chunk_id"] is not None
        assert citation["page_start"] in [1, 2, 3]
        assert citation["score"] > 0.0
        # Verify content was extracted directly from our uploaded PDF
        assert any(
            "entangle" in c["excerpt"].lower() or "qubit" in c["excerpt"].lower()
            for c in data["citations"]
        )

    # 6. Test Context Debugging Endpoint
    ctx_res = client.get(
        f"/api/tutor/course/{course_id}/context?q=shor%20factorization&min_score=0.10"
    )
    assert ctx_res.status_code == 200
    ctx_data = ctx_res.json()
    assert ctx_data["chunks_count"] >= 1
    assert any("quantum" in c["excerpt"].lower() or "qubit" in c["excerpt"].lower() for c in ctx_data["chunks"])

    # 7. Self-Healing Test: Remove/Corrupt vector index and verify automatic recovery
    # Delete from in-memory cache
    store._cache.pop(course_id, None)
    # Delete index file from disk
    index_file = store._index_path_for_course(course_id)
    if index_file.exists():
        index_file.unlink()

    assert not store.has_course_index(course_id), "Index should be deleted for self-healing test"

    # Tutor query should automatically trigger ensure_course_vector_index self-healing
    with patch.dict(os.environ, {"TEST_MODE": "true"}):
        heal_res = client.post(
            f"/api/tutor/course/{course_id}/ask",
            json={
                "question": "Explain Shor's algorithm for integer factorization",
                "min_score": 0.10,
            },
        )
        assert heal_res.status_code == 200, f"Self-healing query failed: {heal_res.text}"
        heal_data = heal_res.json()

        assert heal_data["is_refusal"] is False
        assert len(heal_data["citations"]) >= 1
        assert "shor" in heal_data["answer"].lower() or "factorization" in heal_data["answer"].lower()

        # Confirm the index file and cache were reconstructed on disk
        assert store.has_course_index(course_id), "Index was not self-healed!"
        assert index_file.exists(), "Rebuilt index file was not persisted to disk!"


def test_rag_cross_course_isolation_e2e(client):
    """
    Verifies that two independently generated courses have strict vector isolation.
    Course B must not retrieve or cite chunks from Course A.
    """
    # Create Course A (Quantum)
    up_q = client.post(
        "/api/courses/upload",
        files={"file": ("quantum.pdf", io.BytesIO(create_quantum_pdf_bytes()), "application/pdf")},
    )
    course_a = client.post(
        "/api/courses/",
        json={"title": "Quantum Physics", "document_id": up_q.json()["document_id"]},
    ).json()["id"]

    with patch("api.course_generation.generate_course_from_chunks", return_value=mock_quantum_curriculum()):
        client.post(f"/api/courses/{course_a}/generate")

    # Create Course B (Economics)
    up_e = client.post(
        "/api/courses/upload",
        files={"file": ("economics.pdf", io.BytesIO(create_economics_pdf_bytes()), "application/pdf")},
    )
    course_b = client.post(
        "/api/courses/",
        json={"title": "Microeconomics 101", "document_id": up_e.json()["document_id"]},
    ).json()["id"]

    with patch("api.course_generation.generate_course_from_chunks", return_value=mock_quantum_curriculum()):
        client.post(f"/api/courses/{course_b}/generate")

    with patch.dict(os.environ, {"TEST_MODE": "true"}):
        # Query Course B (Economics) about Quantum Superposition
        res = client.post(
            f"/api/tutor/course/{course_b}/ask",
            json={"question": "Explain quantum superposition of qubits", "min_score": 0.15},
        )
        assert res.status_code == 200
        data = res.json()
        # Must refuse because Course B has zero quantum chunks
        assert data["is_refusal"] is True
        assert data["citations"] == []

        # Query Course B about Supply and Demand
        res_econ = client.post(
            f"/api/tutor/course/{course_b}/ask",
            json={"question": "Explain supply and demand equilibrium in competitive markets", "min_score": 0.15},
        )
        assert res_econ.status_code == 200
        data_econ = res_econ.json()
        assert data_econ["is_refusal"] is False
        assert len(data_econ["citations"]) >= 1
        assert "supply" in data_econ["citations"][0]["excerpt"].lower()
