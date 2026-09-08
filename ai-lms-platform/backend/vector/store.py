"""
vector/store.py - In-Memory and Persistent Vector Store for Course Knowledge Bases.

Stores and queries document chunks partitioned strictly by course_id.
Uses cosine similarity search over normalized embeddings.
Persists course indexes to disk under backend/storage/vectors/ for rebuildability.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

from vector.embeddings import get_embedding_engine, embed_text, EmbeddingEngine

logger = logging.getLogger("lms.vector.store")

# Storage directory for vector indexes
VECTOR_STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage" / "vectors"
VECTOR_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class VectorChunk:
    """Represents an indexed document chunk with RAG citations and embedding."""
    course_id: int
    chunk_id: str
    text: str
    page_start: int
    page_end: int
    section: str
    embedding: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VectorChunk":
        return cls(
            course_id=int(data.get("course_id", 0)),
            chunk_id=str(data.get("chunk_id", "")),
            text=str(data.get("text", "")),
            page_start=int(data.get("page_start", 1)),
            page_end=int(data.get("page_end", 1)),
            section=str(data.get("section", "General")),
            embedding=list(data.get("embedding", [])),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class SearchResult:
    """Result item returned by semantic similarity search."""
    chunk_id: str
    text: str
    score: float
    page_start: int
    page_end: int
    section: str
    course_id: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VectorStore:
    """
    Manages vector indexing, cosine similarity retrieval, and persistence
    partitioned strictly by course_id.
    """

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        embedding_engine: Optional[EmbeddingEngine] = None,
    ):
        self.storage_dir = Path(storage_dir) if storage_dir else VECTOR_STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_engine = embedding_engine or get_embedding_engine()
        # In-memory cache of loaded courses: {course_id: List[VectorChunk]}
        self._cache: Dict[int, List[VectorChunk]] = {}

    def _index_path_for_course(self, course_id: int) -> Path:
        """Returns the file path where a course's vector index is stored."""
        return self.storage_dir / f"course_{course_id}.json"

    def _load_course_index(self, course_id: int) -> List[VectorChunk]:
        """
        Loads course chunks into cache from disk if not already in memory.
        Gracefully handles missing or corrupted index files.
        """
        if course_id in self._cache:
            return self._cache[course_id]

        file_path = self._index_path_for_course(course_id)
        if not file_path.exists():
            self._cache[course_id] = []
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                payload = json.load(f)

            raw_chunks = payload.get("chunks", [])
            loaded_chunks: List[VectorChunk] = []
            for item in raw_chunks:
                try:
                    loaded_chunks.append(VectorChunk.from_dict(item))
                except Exception as parse_err:
                    logger.warning("Skipping malformed chunk in %s: %s", file_path.name, parse_err)

            self._cache[course_id] = loaded_chunks
            return loaded_chunks
        except Exception as exc:
            logger.warning("Failed to load vector index for course %d: %s. Starting with empty index.", course_id, exc)
            self._cache[course_id] = []
            return []

    def _persist_course_index(self, course_id: int) -> None:
        """Saves a course's chunks and metadata to disk atomically."""
        chunks = self._cache.get(course_id, [])
        file_path = self._index_path_for_course(course_id)

        data = {
            "course_id": course_id,
            "chunk_count": len(chunks),
            "chunks": [c.to_dict() for c in chunks],
        }

        temp_path = file_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            temp_path.replace(file_path)
        except Exception as exc:
            logger.error("Failed to persist vector index for course %d: %s", course_id, exc)
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass

    def add_chunks(self, course_id: int, chunks: List[Dict[str, Any]]) -> int:
        """
        Embeds and indexes document chunks for a course.
        Appends to existing course index and persists to disk.
        """
        if not chunks:
            return 0

        existing = self._load_course_index(course_id)
        new_vector_chunks: List[VectorChunk] = []

        for ch in chunks:
            text = ch.get("text", "").strip()
            if not text:
                continue

            # Compute embedding if not already provided
            embedding = ch.get("embedding")
            if not embedding:
                embedding = self.embedding_engine.embed_text(text)

            meta = dict(ch.get("metadata", {}))
            if "word_count" in ch:
                meta["word_count"] = ch["word_count"]
            if "character_count" in ch:
                meta["character_count"] = ch["character_count"]

            vc = VectorChunk(
                course_id=course_id,
                chunk_id=str(ch.get("chunk_id", f"chunk_{len(existing) + len(new_vector_chunks) + 1:03d}")),
                text=text,
                page_start=int(ch.get("page_start", 1)),
                page_end=int(ch.get("page_end", ch.get("page_start", 1))),
                section=str(ch.get("section", "General")),
                embedding=embedding,
                metadata=meta,
            )
            new_vector_chunks.append(vc)

        existing.extend(new_vector_chunks)
        self._cache[course_id] = existing
        self._persist_course_index(course_id)
        return len(new_vector_chunks)

    def replace_course_chunks(self, course_id: int, chunks: List[Dict[str, Any]]) -> int:
        """
        Replaces/rebuilds an entire course index with new chunks.
        Clears previous index in memory and on disk.
        """
        self._cache[course_id] = []
        return self.add_chunks(course_id, chunks)

    def search(
        self,
        query: str,
        course_id: int,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """
        Performs semantic similarity search for a query strictly within course_id chunks.

        Args:
            query: User's question or search phrase.
            course_id: Target course identifier (strict partition).
            top_k: Maximum number of relevant chunks to return.
            min_score: Minimum cosine similarity threshold (0.0 to 1.0).

        Returns:
            List of SearchResult objects sorted by similarity score descending.
        """
        if not query or not query.strip():
            return []

        chunks = self._load_course_index(course_id)
        if not chunks:
            return []

        query_vec = np.array(self.embedding_engine.embed_text(query), dtype=np.float32)
        q_norm = float(np.linalg.norm(query_vec))
        if q_norm < 1e-8:
            return []

        # Build matrix of chunk embeddings
        chunk_embeddings = np.array([c.embedding for c in chunks], dtype=np.float32)
        if chunk_embeddings.size == 0:
            return []

        # Cosine similarity: dot product of normalized vectors
        scores = np.dot(chunk_embeddings, query_vec) / q_norm

        results: List[SearchResult] = []
        for i, score_val in enumerate(scores):
            raw_score = float(score_val)
            # Clamp to [0.0, 1.0]
            norm_score = max(0.0, min(1.0, raw_score))
            if norm_score >= min_score:
                ch = chunks[i]
                results.append(
                    SearchResult(
                        chunk_id=ch.chunk_id,
                        text=ch.text,
                        score=round(norm_score, 4),
                        page_start=ch.page_start,
                        page_end=ch.page_end,
                        section=ch.section,
                        course_id=ch.course_id,
                        metadata=ch.metadata,
                    )
                )

        # Sort descending by score
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def delete_course_index(self, course_id: int) -> bool:
        """
        Deletes a course's vector index from memory and disk.
        Returns True if the index was deleted or existed.
        """
        self._cache.pop(course_id, None)
        file_path = self._index_path_for_course(course_id)
        if file_path.exists():
            try:
                file_path.unlink()
                return True
            except Exception as exc:
                logger.error("Failed to delete index file %s: %s", file_path, exc)
                return False
        return True

    def has_course_index(self, course_id: int) -> bool:
        """Returns True if the course index exists and contains at least one chunk."""
        chunks = self._load_course_index(course_id)
        return len(chunks) > 0

    def count_course_chunks(self, course_id: int) -> int:
        """Returns the number of indexed chunks for a course."""
        chunks = self._load_course_index(course_id)
        return len(chunks)

    def get_course_chunks(self, course_id: int) -> List[Dict[str, Any]]:
        """Returns raw dictionaries of all indexed chunks for a course."""
        chunks = self._load_course_index(course_id)
        return [c.to_dict() for c in chunks]

    def clear_all(self) -> None:
        """Clears all in-memory caches."""
        self._cache.clear()


# Module-level shared instance
_DEFAULT_STORE: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Returns the shared VectorStore singleton."""
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        _DEFAULT_STORE = VectorStore()
    return _DEFAULT_STORE
