"""
tests/test_vector.py - Phase 6 Step 1 Tests: Vector Store & Deterministic Embedding Engine.

Covers:
- Deterministic fallback embeddings (consistency, unit norm, dimensions, empty text)
- Semantic cosine similarity behavior
- Course chunk indexing
- Top-k retrieval and ordering
- Similarity scores and min_score threshold filtering
- Strict course isolation (no cross-course leakage)
- Rebuilding / replacing course index
- Deleting course index
- Empty query and missing index edge cases
- Persistence to disk and reloading
- Preservation of page numbers and section citations
- Corrupted index file recovery
"""

import json
from pathlib import Path
import numpy as np
import pytest

from vector.embeddings import (
    EmbeddingEngine,
    generate_deterministic_embedding,
    embed_text,
    embed_batch,
    DETERMINISTIC_EMBEDDING_DIM,
)
from vector.store import (
    VectorStore,
    VectorChunk,
    SearchResult,
)


@pytest.fixture
def temp_vector_dir(tmp_path: Path) -> Path:
    """Fixture providing an isolated temporary directory for vector persistence tests."""
    v_dir = tmp_path / "vector_test"
    v_dir.mkdir(parents=True, exist_ok=True)
    return v_dir


@pytest.fixture
def local_store(temp_vector_dir: Path) -> VectorStore:
    """Fixture providing a VectorStore with isolated storage and deterministic embedder."""
    engine = EmbeddingEngine(provider="local")
    return VectorStore(storage_dir=temp_vector_dir, embedding_engine=engine)


# --- Embedding Engine Tests ---

def test_deterministic_fallback_embeddings_identical_text():
    """1. Identical text produces the exact same embedding vector every time."""
    text1 = "Binary search algorithms require a sorted list to run in logarithmic time."
    text2 = "Binary search algorithms require a sorted list to run in logarithmic time."
    vec1 = generate_deterministic_embedding(text1)
    vec2 = generate_deterministic_embedding(text2)

    assert vec1 == vec2
    assert len(vec1) == DETERMINISTIC_EMBEDDING_DIM


def test_deterministic_fallback_embeddings_dimension_and_norm():
    """2. Embeddings have the expected dimension and unit L2 norm."""
    text = "Machine learning models optimize parameters using gradient descent."
    vec = generate_deterministic_embedding(text)

    assert len(vec) == DETERMINISTIC_EMBEDDING_DIM
    arr = np.array(vec, dtype=np.float32)
    norm = float(np.linalg.norm(arr))
    assert pytest.approx(norm, abs=1e-4) == 1.0


def test_deterministic_fallback_embeddings_empty_and_whitespace():
    """3. Empty or whitespace strings return zero vectors without crashing."""
    assert generate_deterministic_embedding("") == [0.0] * DETERMINISTIC_EMBEDDING_DIM
    assert generate_deterministic_embedding("   \n\t  ") == [0.0] * DETERMINISTIC_EMBEDDING_DIM


def test_deterministic_fallback_semantic_similarity():
    """4. Semantically related sentences produce higher cosine similarity than unrelated ones."""
    query = "database indexing and relational tables"
    doc_related = "Relational database tables use B-tree indexing for fast query performance."
    doc_unrelated = "Photosynthesis in green plants converts solar sunlight into chemical energy."

    q_vec = np.array(generate_deterministic_embedding(query))
    rel_vec = np.array(generate_deterministic_embedding(doc_related))
    unrel_vec = np.array(generate_deterministic_embedding(doc_unrelated))

    sim_related = float(np.dot(q_vec, rel_vec))
    sim_unrelated = float(np.dot(q_vec, unrel_vec))

    assert sim_related > sim_unrelated
    assert sim_related > 0.4
    assert sim_unrelated < 0.2


def test_embed_batch():
    """5. embed_batch produces batch embeddings consistently."""
    texts = [
        "First document about algorithms.",
        "Second document about networks.",
        "",
    ]
    batch_vecs = embed_batch(texts)
    assert len(batch_vecs) == 3
    assert len(batch_vecs[0]) == DETERMINISTIC_EMBEDDING_DIM
    assert batch_vecs[2] == [0.0] * DETERMINISTIC_EMBEDDING_DIM


# --- Vector Store Tests ---

def test_vector_store_indexing(local_store: VectorStore):
    """6. Indexing chunks stores them in the course index and persists to disk."""
    chunks = [
        {
            "chunk_id": "chunk_001",
            "text": "Introduction to Data Structures and Arrays.",
            "page_start": 1,
            "page_end": 2,
            "section": "Chapter 1",
            "word_count": 45,
        },
        {
            "chunk_id": "chunk_002",
            "text": "Linked Lists and Dynamic Memory Allocation.",
            "page_start": 3,
            "page_end": 4,
            "section": "Chapter 2",
            "word_count": 52,
        },
    ]

    count = local_store.add_chunks(course_id=1, chunks=chunks)
    assert count == 2
    assert local_store.count_course_chunks(course_id=1) == 2
    assert local_store.has_course_index(course_id=1) is True


def test_vector_store_retrieval(local_store: VectorStore):
    """7. Semantic search retrieves the most relevant chunk with highest score."""
    chunks = [
        {
            "chunk_id": "chunk_001",
            "text": "Binary search trees allow efficient searching, insertion, and deletion operations.",
            "page_start": 10,
            "page_end": 12,
            "section": "Trees",
        },
        {
            "chunk_id": "chunk_002",
            "text": "Network protocols define rules for packet routing across the global Internet.",
            "page_start": 20,
            "page_end": 22,
            "section": "Networking",
        },
    ]
    local_store.add_chunks(course_id=10, chunks=chunks)

    results = local_store.search(query="tree search algorithms", course_id=10, top_k=1)
    assert len(results) == 1
    assert results[0].chunk_id == "chunk_001"
    assert "binary search trees" in results[0].text.lower()
    assert results[0].score > 0.25
    assert results[0].page_start == 10
    assert results[0].section == "Trees"


def test_vector_store_top_k_behavior(local_store: VectorStore):
    """8. top_k restricts the maximum number of returned results."""
    chunks = [
        {"chunk_id": f"chunk_{i:03d}", "text": f"Algorithmic complexity chapter section {i}.", "page_start": i, "page_end": i, "section": "Complexity"}
        for i in range(1, 6)
    ]
    local_store.add_chunks(course_id=5, chunks=chunks)

    results_k2 = local_store.search(query="algorithmic complexity", course_id=5, top_k=2)
    assert len(results_k2) == 2

    results_k4 = local_store.search(query="algorithmic complexity", course_id=5, top_k=4)
    assert len(results_k4) == 4


def test_vector_store_similarity_threshold(local_store: VectorStore):
    """9. min_score filters out chunks that fall below the required threshold."""
    chunks = [
        {"chunk_id": "chunk_rel", "text": "Operating system process scheduling and context switching.", "page_start": 1, "page_end": 2, "section": "OS"},
        {"chunk_id": "chunk_unrel", "text": "Cooking pasta and culinary culinary kitchen recipes.", "page_start": 5, "page_end": 6, "section": "Cooking"},
    ]
    local_store.add_chunks(course_id=7, chunks=chunks)

    # Search for OS concepts with high threshold
    results = local_store.search(query="operating system scheduling", course_id=7, top_k=5, min_score=0.3)
    chunk_ids = [r.chunk_id for r in results]
    assert "chunk_rel" in chunk_ids
    assert "chunk_unrel" not in chunk_ids


def test_vector_store_course_isolation(local_store: VectorStore):
    """10. Search results are strictly scoped to the specified course_id."""
    course1_chunks = [
        {"chunk_id": "c1_ch1", "text": "Linear regression and supervised machine learning.", "page_start": 1, "page_end": 2, "section": "ML"},
    ]
    course2_chunks = [
        {"chunk_id": "c2_ch1", "text": "Database normalization and first normal form.", "page_start": 1, "page_end": 2, "section": "DB"},
    ]

    local_store.add_chunks(course_id=1, chunks=course1_chunks)
    local_store.add_chunks(course_id=2, chunks=course2_chunks)

    res_c1 = local_store.search(query="machine learning", course_id=1, top_k=5)
    assert len(res_c1) == 1
    assert res_c1[0].chunk_id == "c1_ch1"
    assert res_c1[0].course_id == 1

    res_c2 = local_store.search(query="machine learning", course_id=2, top_k=5)
    # Course 2 does not have ML chunks, or if any score, course_id must be 2
    for r in res_c2:
        assert r.course_id == 2


def test_no_cross_course_retrieval(local_store: VectorStore):
    """11. Querying course 1 never returns chunks belonging to course 2."""
    local_store.add_chunks(course_id=1, chunks=[
        {"chunk_id": "c1_chunk", "text": "Cellular biology and mitochondria function.", "page_start": 1, "page_end": 2, "section": "Bio"}
    ])
    local_store.add_chunks(course_id=2, chunks=[
        {"chunk_id": "c2_chunk", "text": "Quantum computing and qubit superposition.", "page_start": 1, "page_end": 2, "section": "Physics"}
    ])

    # Search for quantum in Course 1
    results = local_store.search(query="quantum qubit superposition", course_id=1, top_k=5)
    chunk_ids = [r.chunk_id for r in results]
    assert "c2_chunk" not in chunk_ids


def test_vector_store_replacing_rebuilding_index(local_store: VectorStore):
    """12. replace_course_chunks clears previous index and rebuilds anew."""
    old_chunks = [
        {"chunk_id": "old_01", "text": "Old obsolete curriculum content.", "page_start": 1, "page_end": 1, "section": "Old"}
    ]
    local_store.add_chunks(course_id=99, chunks=old_chunks)
    assert local_store.count_course_chunks(course_id=99) == 1

    new_chunks = [
        {"chunk_id": "new_01", "text": "Brand new modern syllabus content.", "page_start": 1, "page_end": 2, "section": "New 1"},
        {"chunk_id": "new_02", "text": "Second modern lesson content.", "page_start": 3, "page_end": 4, "section": "New 2"},
    ]
    rebuilt_count = local_store.replace_course_chunks(course_id=99, chunks=new_chunks)
    assert rebuilt_count == 2
    assert local_store.count_course_chunks(course_id=99) == 2

    # Verify old chunk is gone
    res = local_store.search(query="obsolete", course_id=99, top_k=5)
    for r in res:
        assert r.chunk_id != "old_01"


def test_vector_store_deleting_index(local_store: VectorStore):
    """13. delete_course_index clears index from memory and disk."""
    chunks = [
        {"chunk_id": "temp_ch", "text": "Temporary topic text.", "page_start": 1, "page_end": 1, "section": "Temp"}
    ]
    local_store.add_chunks(course_id=42, chunks=chunks)
    assert local_store.has_course_index(course_id=42) is True

    deleted = local_store.delete_course_index(course_id=42)
    assert deleted is True
    assert local_store.has_course_index(course_id=42) is False
    assert local_store.count_course_chunks(course_id=42) == 0

    # Search returns empty
    assert local_store.search(query="temporary", course_id=42) == []


def test_empty_or_invalid_query_handling(local_store: VectorStore):
    """14. Empty or whitespace query returns empty list without error."""
    chunks = [
        {"chunk_id": "ch1", "text": "Valid text chunk.", "page_start": 1, "page_end": 1, "section": "General"}
    ]
    local_store.add_chunks(course_id=1, chunks=chunks)

    assert local_store.search("", course_id=1) == []
    assert local_store.search("   \n\t ", course_id=1) == []


def test_missing_course_index_handling(local_store: VectorStore):
    """15. Querying a non-existent course returns empty list gracefully."""
    assert local_store.has_course_index(course_id=9999) is False
    results = local_store.search("test query", course_id=9999)
    assert results == []


def test_persistence_and_reload(temp_vector_dir: Path):
    """16. Newly instantiated VectorStore reloads existing index files from disk."""
    engine = EmbeddingEngine(provider="local")
    store1 = VectorStore(storage_dir=temp_vector_dir, embedding_engine=engine)

    chunks = [
        {
            "chunk_id": "persist_01",
            "text": "Microservices and distributed consensus algorithms.",
            "page_start": 5,
            "page_end": 7,
            "section": "Distributed Systems",
        }
    ]
    store1.add_chunks(course_id=88, chunks=chunks)

    # Instantiate fresh store pointing to same directory
    store2 = VectorStore(storage_dir=temp_vector_dir, embedding_engine=engine)
    assert store2.has_course_index(course_id=88) is True
    assert store2.count_course_chunks(course_id=88) == 1

    results = store2.search("consensus algorithms", course_id=88, top_k=1)
    assert len(results) == 1
    assert results[0].chunk_id == "persist_01"
    assert results[0].page_start == 5
    assert results[0].page_end == 7


def test_preservation_of_citations_and_metadata(local_store: VectorStore):
    """17. SearchResult preserves page_start, page_end, section, and extra metadata."""
    chunks = [
        {
            "chunk_id": "cite_01",
            "text": "Deep neural networks use backpropagation to calculate error gradients.",
            "page_start": 42,
            "page_end": 44,
            "section": "Chapter 4: Neural Networks",
            "metadata": {"author": "Lecturer", "difficulty": "advanced"},
        }
    ]
    local_store.add_chunks(course_id=12, chunks=chunks)

    results = local_store.search("backpropagation error gradients", course_id=12, top_k=1)
    assert len(results) == 1
    res = results[0]
    assert res.page_start == 42
    assert res.page_end == 44
    assert res.section == "Chapter 4: Neural Networks"
    assert res.metadata.get("difficulty") == "advanced"


def test_corrupted_index_file_handled_gracefully(temp_vector_dir: Path):
    """18. Corrupted index JSON file is handled gracefully without crashing."""
    corrupted_file = temp_vector_dir / "course_777.json"
    corrupted_file.write_text("NOT_VALID_JSON{{{", encoding="utf-8")

    engine = EmbeddingEngine(provider="local")
    store = VectorStore(storage_dir=temp_vector_dir, embedding_engine=engine)

    # Should not raise exception
    assert store.has_course_index(course_id=777) is False
    assert store.search("anything", course_id=777) == []
