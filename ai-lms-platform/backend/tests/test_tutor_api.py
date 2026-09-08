"""
tests/test_tutor_api.py - Phase 6 Step 3 Tests: AI Tutor API & Schemas.

Covers:
1. Health / status endpoint (GET /api/tutor/).
2. Successful tutor question with citations and mocked Gemini.
3. Fallback tutor response (offline / TEST_MODE / LLM failure).
4. Nonexistent course returns 404.
5. Course without source material returns 400.
6. Empty or blank whitespace question returns 400/422.
7. Validation of top_k and min_score/similarity_threshold bounds (422).
8. Unsupported question returns safe refusal response.
9. Unindexed course returns safe refusal response without crashing.
10. Strict course isolation (Course A cannot retrieve or cite chunks from Course B).
11. Context inspection endpoint (GET /api/tutor/course/{id}/context) success.
12. Context inspection 404 for missing course and 400 for no source material.
13. Context inspection empty query rejection.
14. Context inspection strict course isolation.
15. Similarity threshold alias support in request schema.
16. Internal error sanitization (does not leak internal exceptions or keys).
"""

import os
from pathlib import Path
from unittest.mock import patch
import pytest

from database.models import User, Course
from tests.conftest import TestingSessionLocal
from vector.store import VectorStore
from vector.embeddings import EmbeddingEngine


@pytest.fixture
def test_db():
    """Provides a fresh database session for seeding courses and teachers."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def isolated_tutor_store(tmp_path: Path):
    """Provides an isolated VectorStore backed by tmp_path for API tests."""
    engine = EmbeddingEngine(provider="local")
    store = VectorStore(storage_dir=tmp_path / "api_test_vectors", embedding_engine=engine)

    with patch("vector.store.get_vector_store", return_value=store), \
         patch("api.tutor.get_vector_store", return_value=store), \
         patch("ai.tutor.get_vector_store", return_value=store):
        yield store


def seed_test_course(
    db,
    title: str = "Data Structures & Algorithms",
    source_file: str = "dsa_textbook.pdf",
) -> Course:
    """Helper creating teacher and course record in the test database."""
    teacher = User(
        name="Dr. Turing",
        email=f"turing_{title[:5].lower()}@lms.local",
        role="teacher",
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)

    course = Course(
        title=title,
        description="Comprehensive course on data structures and algorithms.",
        source_file=source_file,
        teacher_id=teacher.id,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


# ===========================================================================
# 1. Health & Status
# ===========================================================================

def test_tutor_status_endpoint(client):
    """Verify GET /api/tutor/ returns 200 and ready status."""
    res = client.get("/api/tutor/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert "AI Tutor" in data["service"]


# ===========================================================================
# 2. Course & Question Validation (HTTP 404, 400, 422)
# ===========================================================================

def test_ask_tutor_course_not_found(client):
    """Verify 404 when querying a nonexistent course."""
    res = client.post(
        "/api/tutor/course/99999/ask",
        json={"question": "What is a binary search tree?"},
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_ask_tutor_course_without_source_file(client, test_db):
    """Verify 400 when course exists but has no source material."""
    course = seed_test_course(test_db, title="Empty Course", source_file=None)

    res = client.post(
        f"/api/tutor/course/{course.id}/ask",
        json={"question": "What is a binary search tree?"},
    )
    assert res.status_code == 400
    assert "source material" in res.json()["detail"].lower()


def test_ask_tutor_empty_or_whitespace_question(client, test_db):
    """Verify empty or whitespace questions are rejected with 400 or 422."""
    course = seed_test_course(test_db)

    # Empty string
    res_empty = client.post(
        f"/api/tutor/course/{course.id}/ask",
        json={"question": ""},
    )
    assert res_empty.status_code in (400, 422)

    # Whitespace only
    res_ws = client.post(
        f"/api/tutor/course/{course.id}/ask",
        json={"question": "     "},
    )
    assert res_ws.status_code in (400, 422)

    # Missing question key
    res_missing = client.post(
        f"/api/tutor/course/{course.id}/ask",
        json={},
    )
    assert res_missing.status_code == 422


def test_ask_tutor_validation_bounds_top_k_and_min_score(client, test_db):
    """Verify top_k and min_score out of bounds are rejected with 422."""
    course = seed_test_course(test_db)

    # top_k < 1
    res1 = client.post(
        f"/api/tutor/course/{course.id}/ask",
        json={"question": "Valid question", "top_k": 0},
    )
    assert res1.status_code == 422

    # top_k > 10
    res2 = client.post(
        f"/api/tutor/course/{course.id}/ask",
        json={"question": "Valid question", "top_k": 11},
    )
    assert res2.status_code == 422

    # min_score < 0.0
    res3 = client.post(
        f"/api/tutor/course/{course.id}/ask",
        json={"question": "Valid question", "min_score": -0.5},
    )
    assert res3.status_code == 422

    # min_score > 1.0
    res4 = client.post(
        f"/api/tutor/course/{course.id}/ask",
        json={"question": "Valid question", "min_score": 1.5},
    )
    assert res4.status_code == 422


# ===========================================================================
# 3. Successful Tutor Queries, Citations & Fallback
# ===========================================================================

def test_ask_tutor_successful_question_with_mocked_gemini(client, test_db, isolated_tutor_store):
    """Verify successful response with citations when Gemini succeeds."""
    course = seed_test_course(test_db)

    # Index relevant chunks
    isolated_tutor_store.add_chunks(
        course_id=course.id,
        chunks=[
            {
                "chunk_id": "bst_001",
                "text": (
                    "A Binary Search Tree (BST) is a hierarchical node-based data structure. "
                    "For each node, keys in the left subtree are strictly less, and keys in the "
                    "right subtree are strictly greater. Search, insert, and delete operations "
                    "have an average time complexity of O(log n)."
                ),
                "page_start": 25,
                "page_end": 26,
                "section": "Binary Trees",
            }
        ],
    )

    mock_llm_json = {
        "answer": "A Binary Search Tree (BST) is an ordered tree where left children have smaller keys and right children have larger keys.",
        "cannot_answer": False,
    }

    with patch("ai.tutor.get_gemini_config", return_value=("fake_api_key", "models/gemini-1.5-pro")), \
         patch.dict(os.environ, {"TEST_MODE": "false"}), \
         patch("ai.tutor.call_gemini_json", return_value=mock_llm_json):

        res = client.post(
            f"/api/tutor/course/{course.id}/ask",
            json={"question": "What is a binary search tree?", "top_k": 3, "min_score": 0.15},
        )

    assert res.status_code == 200
    data = res.json()

    assert data["course_id"] == course.id
    assert "Binary Search Tree" in data["answer"]
    assert data["is_fallback"] is False
    assert data["is_refusal"] is False
    assert data["confidence"] > 0.0
    assert len(data["citations"]) >= 1

    citation = data["citations"][0]
    assert citation["chunk_id"] == "bst_001"
    assert citation["page_start"] == 25
    assert citation["page_end"] == 26
    assert citation["section"] == "Binary Trees"
    assert "Binary Search Tree" in citation["excerpt"]
    assert citation["score"] > 0.0


def test_ask_tutor_deterministic_fallback_response(client, test_db, isolated_tutor_store):
    """Verify deterministic grounded fallback answer when offline or in TEST_MODE."""
    course = seed_test_course(test_db)

    isolated_tutor_store.add_chunks(
        course_id=course.id,
        chunks=[
            {
                "chunk_id": "sort_001",
                "text": (
                    "Quicksort is an efficient divide-and-conquer sorting algorithm. "
                    "It works by selecting a pivot element and partitioning the array. "
                    "Average time complexity is O(n log n)."
                ),
                "page_start": 40,
                "page_end": 41,
                "section": "Sorting Algorithms",
            }
        ],
    )

    with patch.dict(os.environ, {"TEST_MODE": "true"}):
        res = client.post(
            f"/api/tutor/course/{course.id}/ask",
            json={"question": "Explain how quicksort works", "top_k": 2, "min_score": 0.15},
        )

    assert res.status_code == 200
    data = res.json()

    assert data["course_id"] == course.id
    assert data["is_fallback"] is True
    assert data["is_refusal"] is False
    assert "Quicksort" in data["answer"]
    assert len(data["citations"]) >= 1
    assert data["citations"][0]["chunk_id"] == "sort_001"


def test_ask_tutor_unsupported_question_refusal(client, test_db, isolated_tutor_store):
    """Verify conservative guardrail refusal for unsupported/out-of-scope query."""
    course = seed_test_course(test_db)

    isolated_tutor_store.add_chunks(
        course_id=course.id,
        chunks=[
            {
                "chunk_id": "cs_001",
                "text": "Data structures organize and store data for efficient access and modification.",
                "page_start": 1,
                "page_end": 2,
                "section": "Introduction",
            }
        ],
    )

    # Submit totally unrelated question with default threshold
    res = client.post(
        f"/api/tutor/course/{course.id}/ask",
        json={"question": "How do you bake a chocolate cake?", "min_score": 0.50},
    )

    assert res.status_code == 200
    data = res.json()

    assert data["is_refusal"] is True
    assert data["citations"] == []
    assert data["confidence"] == 0.0
    assert "cannot find information" in data["answer"].lower()


def test_ask_tutor_default_threshold_refuses_unrelated_capital_of_france(client, test_db, isolated_tutor_store):
    """Verify default min_score=0.20 refuses unrelated query 'What is the capital of France?'."""
    course = seed_test_course(test_db, title="Harassment Prevention Course")

    isolated_tutor_store.add_chunks(
        course_id=course.id,
        chunks=[
            {
                "chunk_id": "chunk_002",
                "text": (
                    "The policy prohibits all forms of harassment including verbal harassment, "
                    "physical harassment, and visual harassment."
                ),
                "page_start": 2,
                "page_end": 2,
                "section": "Types of Harassment",
            },
            {
                "chunk_id": "chunk_003",
                "text": "Taking Action: If you experience harassment, report it immediately to HR.",
                "page_start": 3,
                "page_end": 3,
                "section": "Taking Action",
            },
        ],
    )

    # Submit unrelated question with default threshold (no min_score specified)
    with patch.dict(os.environ, {"TEST_MODE": "true"}):
        res = client.post(
            f"/api/tutor/course/{course.id}/ask",
            json={"question": "What is the capital of France?"},
        )

    assert res.status_code == 200
    data = res.json()
    assert data["is_refusal"] is True
    assert data["citations"] == []
    assert data["confidence"] == 0.0
    assert "cannot find information" in data["answer"].lower()


def test_ask_tutor_unindexed_course_safe_response(client, test_db, isolated_tutor_store):
    """Verify safe refusal response when a course has source_file but no indexed chunks."""
    course = seed_test_course(test_db, title="Unindexed Course", source_file="empty.pdf")

    # Do not add any chunks to isolated_tutor_store for this course_id
    res = client.post(
        f"/api/tutor/course/{course.id}/ask",
        json={"question": "What is an algorithm?"},
    )

    assert res.status_code == 200
    data = res.json()

    assert data["is_refusal"] is True
    assert data["citations"] == []
    assert data["confidence"] == 0.0
    assert "cannot find information" in data["answer"].lower()


# ===========================================================================
# 4. Strict Course Isolation
# ===========================================================================

def test_ask_tutor_strict_course_isolation(client, test_db, isolated_tutor_store):
    """Verify Course A cannot access or cite chunks indexed under Course B."""
    course_physics = seed_test_course(test_db, title="Quantum Physics", source_file="physics.pdf")
    course_lit = seed_test_course(test_db, title="English Literature", source_file="literature.pdf")

    # Physics has Quantum Mechanics
    isolated_tutor_store.add_chunks(
        course_id=course_physics.id,
        chunks=[
            {
                "chunk_id": "phys_001",
                "text": "Schrodinger's equation describes the wave function of a quantum-mechanical system.",
                "page_start": 10,
                "page_end": 12,
                "section": "Wave Mechanics",
            }
        ],
    )

    # Literature has Shakespeare
    isolated_tutor_store.add_chunks(
        course_id=course_lit.id,
        chunks=[
            {
                "chunk_id": "lit_001",
                "text": "Hamlet is a tragedy written by William Shakespeare exploring grief and revenge.",
                "page_start": 5,
                "page_end": 6,
                "section": "Shakespearean Tragedies",
            }
        ],
    )

    with patch.dict(os.environ, {"TEST_MODE": "true"}):
        # Query Physics course about Shakespeare -> Must NOT return or cite Literature chunk!
        res_physics = client.post(
            f"/api/tutor/course/{course_physics.id}/ask",
            json={"question": "Tell me about William Shakespeare and Hamlet tragedy", "min_score": 0.15},
        )
        assert res_physics.status_code == 200
        data_phys = res_physics.json()
        assert data_phys["is_refusal"] is True
        assert data_phys["citations"] == []

        # Query Literature course about Shakespeare -> Must retrieve lit_001
        res_lit = client.post(
            f"/api/tutor/course/{course_lit.id}/ask",
            json={"question": "Tell me about William Shakespeare and Hamlet tragedy", "min_score": 0.15},
        )
        assert res_lit.status_code == 200
        data_lit = res_lit.json()
        assert data_lit["is_refusal"] is False
        assert len(data_lit["citations"]) == 1
        assert data_lit["citations"][0]["chunk_id"] == "lit_001"


# ===========================================================================
# 5. Context Debugging & Inspection Endpoint
# ===========================================================================

def test_get_tutor_context_success(client, test_db, isolated_tutor_store):
    """Verify GET /api/tutor/course/{course_id}/context returns indexed chunks."""
    course = seed_test_course(test_db)

    isolated_tutor_store.add_chunks(
        course_id=course.id,
        chunks=[
            {
                "chunk_id": "ctx_001",
                "text": "Recursion occurs when a function calls itself directly or indirectly.",
                "page_start": 50,
                "page_end": 51,
                "section": "Recursion",
            }
        ],
    )

    res = client.get(
        f"/api/tutor/course/{course.id}/context?q=recursion&top_k=2&min_score=0.1"
    )
    assert res.status_code == 200
    data = res.json()

    assert data["course_id"] == course.id
    assert data["query"] == "recursion"
    assert data["chunks_count"] == 1
    assert len(data["chunks"]) == 1
    assert data["chunks"][0]["chunk_id"] == "ctx_001"
    assert data["chunks"][0]["section"] == "Recursion"
    assert "recursion" in data["chunks"][0]["excerpt"].lower()


def test_get_tutor_context_not_found_and_no_source(client, test_db):
    """Verify 404 for nonexistent course and 400 for course without source material."""
    # 404
    res_404 = client.get("/api/tutor/course/99999/context?q=test")
    assert res_404.status_code == 404

    # 400 (no source)
    course_no_source = seed_test_course(test_db, title="No Material", source_file=None)
    res_400 = client.get(f"/api/tutor/course/{course_no_source.id}/context?q=test")
    assert res_400.status_code == 400


def test_get_tutor_context_empty_query(client, test_db):
    """Verify empty or whitespace query is rejected with 400 or 422."""
    course = seed_test_course(test_db)

    res_empty = client.get(f"/api/tutor/course/{course.id}/context?q=")
    assert res_empty.status_code in (400, 422)

    res_ws = client.get(f"/api/tutor/course/{course.id}/context?q=%20%20%20")
    assert res_ws.status_code in (400, 422)


def test_get_tutor_context_strict_course_isolation(client, test_db, isolated_tutor_store):
    """Verify context inspection endpoint strictly enforces course isolation."""
    c1 = seed_test_course(test_db, title="Math 101")
    c2 = seed_test_course(test_db, title="Biology 101")

    isolated_tutor_store.add_chunks(
        course_id=c1.id,
        chunks=[{"chunk_id": "math_01", "text": "Linear algebra studies vector spaces.", "page_start": 1, "page_end": 2, "section": "Vectors"}],
    )
    isolated_tutor_store.add_chunks(
        course_id=c2.id,
        chunks=[{"chunk_id": "bio_01", "text": "Cellular respiration produces ATP.", "page_start": 1, "page_end": 2, "section": "Cells"}],
    )

    # Inspect c1 for biology query
    res = client.get(f"/api/tutor/course/{c1.id}/context?q=cellular%20respiration&min_score=0.2")
    assert res.status_code == 200
    data = res.json()
    assert data["chunks_count"] == 0
    assert data["chunks"] == []


# ===========================================================================
# 6. Schema Aliases & Error Sanitization
# ===========================================================================

def test_ask_tutor_similarity_threshold_alias(client, test_db, isolated_tutor_store):
    """Verify similarity_threshold alias is recognized and respected."""
    course = seed_test_course(test_db)

    isolated_tutor_store.add_chunks(
        course_id=course.id,
        chunks=[{"chunk_id": "c1", "text": "Graphs consist of vertices and edges.", "page_start": 1, "page_end": 1, "section": "Graphs"}],
    )

    with patch.dict(os.environ, {"TEST_MODE": "true"}):
        res = client.post(
            f"/api/tutor/course/{course.id}/ask",
            json={"question": "What is a graph?", "similarity_threshold": 0.15},
        )
        assert res.status_code == 200
        assert res.json()["is_refusal"] is False


def test_ask_tutor_internal_error_sanitization(client, test_db):
    """Verify internal unhandled errors do not leak stack traces or secrets."""
    course = seed_test_course(test_db)

    with patch("api.tutor.ask_tutor", side_effect=RuntimeError("Secret_DB_Key_999 crashed")):
        res = client.post(
            f"/api/tutor/course/{course.id}/ask",
            json={"question": "What is a graph?"},
        )

    assert res.status_code == 500
    assert "Secret_DB_Key_999" not in res.text
    assert "An error occurred" in res.json()["detail"]
