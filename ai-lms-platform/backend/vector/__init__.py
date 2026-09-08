"""
vector - Vector Store and Embedding Engine for RAG Knowledge Base.
"""

from .embeddings import (
    EmbeddingEngine,
    get_embedding_engine,
    embed_text,
    embed_batch,
    generate_deterministic_embedding,
    DETERMINISTIC_EMBEDDING_DIM,
)
from .store import (
    VectorStore,
    get_vector_store,
    VectorChunk,
    SearchResult,
    VECTOR_STORAGE_DIR,
)
from .service import ensure_course_vector_index

__all__ = [
    "EmbeddingEngine",
    "get_embedding_engine",
    "embed_text",
    "embed_batch",
    "generate_deterministic_embedding",
    "DETERMINISTIC_EMBEDDING_DIM",
    "VectorStore",
    "get_vector_store",
    "VectorChunk",
    "SearchResult",
    "VECTOR_STORAGE_DIR",
    "ensure_course_vector_index",
]
