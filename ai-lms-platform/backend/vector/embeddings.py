"""
vector/embeddings.py - Embedding Engine for RAG Knowledge Base.

Provides:
- Clean embedding interface for single text and batch inputs.
- Dual-provider strategy:
  1. Live Gemini embeddings (text-embedding-004) via httpx when configured and reachable.
  2. Deterministic local fallback using feature-hashing n-grams and L2 normalization
     for offline development, CI/CD, and fast repeatable testing without live API keys.
"""

import hashlib
import logging
import os
import re
from typing import Any, Dict, List, Optional
import httpx
import numpy as np

logger = logging.getLogger("lms.vector.embeddings")

DETERMINISTIC_EMBEDDING_DIM = 256
GEMINI_EMBEDDING_MODEL = "text-embedding-004"


DETERMINISTIC_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "can",
    "could", "will", "would", "should", "what", "which", "who", "whom",
    "this", "that", "these", "those", "am", "it", "its", "if", "how", "why",
    "i", "me", "my", "you", "your",
}


def _stem_token(w: str) -> str:
    """Lightweight suffix trimmer for improved morphological token matching."""
    w_clean = w.lower()
    for suffix in ("ing", "tions", "tion", "ies", "es", "s", "ed", "al", "ment", "ic"):
        if len(w_clean) > len(suffix) + 2 and w_clean.endswith(suffix):
            return w_clean[:-len(suffix)]
    return w_clean


def generate_deterministic_embedding(text: str, dim: int = DETERMINISTIC_EMBEDDING_DIM) -> List[float]:
    """
    Generates a deterministic, normalized feature-hash embedding vector from text.

    Guarantees:
    - Consistent vectors for identical input strings across platforms and runs.
    - Filters high-frequency stopwords to maintain a low noise floor and eliminate false-positive matches.
    - Captures word stems, word bigrams, and character trigrams.
    - High cosine similarity for semantically related token distributions.
    - Safe handling of empty or whitespace strings (returns zeros).
    - Unit L2-norm so dot product equals cosine similarity.
    """
    if not text or not text.strip():
        return [0.0] * dim

    raw_words = re.findall(r"\w+", text.lower())
    if not raw_words:
        return [0.0] * dim

    # Apply lightweight morphological normalization and filter high-frequency stopwords
    stems = [_stem_token(w) for w in raw_words]
    filtered_words = [w for w in stems if w not in DETERMINISTIC_STOPWORDS and len(w) > 1]
    # If all tokens were stopwords (e.g. 'to be or not to be'), fall back to stems so we don't produce zero vector
    words = filtered_words if filtered_words else stems
    vec = np.zeros(dim, dtype=np.float32)

    # 1. Word unigram hashing with sign-hashing trick to reduce hash collision bias
    for w in words:
        h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 16) & 1) == 0 else -1.0
        weight = 1.0 + np.log(1.0 + len(w))
        vec[idx] += sign * weight

    # 2. Word bigram hashing for phrase structure
    for i in range(len(words) - 1):
        bigram = f"{words[i]}_{words[i+1]}"
        h = int(hashlib.md5(bigram.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 16) & 1) == 0 else -1.0
        vec[idx] += sign * 1.5

    # 3. Character trigram hashing for morphology and subword overlap
    joined = " ".join(words)
    for i in range(len(joined) - 2):
        trigram = joined[i : i + 3]
        h = int(hashlib.md5(trigram.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 16) & 1) == 0 else -1.0
        vec[idx] += sign * 0.3

    # L2 normalize
    norm = float(np.linalg.norm(vec))
    if norm > 1e-8:
        vec = vec / norm
    else:
        vec = np.zeros(dim, dtype=np.float32)

    return vec.tolist()


def generate_gemini_embedding(
    text: str,
    api_key: str,
    model: str = GEMINI_EMBEDDING_MODEL,
    timeout_seconds: float = 15.0,
) -> Optional[List[float]]:
    """
    Calls Google Gemini REST API text-embedding-004 endpoint.
    Returns normalized embedding vector on success, or None on error.
    """
    if not text or not text.strip():
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={api_key}"
    payload = {
        "content": {
            "parts": [{"text": text[:8000]}]  # Cap length safely
        }
    }

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                values = data.get("embedding", {}).get("values")
                if values and isinstance(values, list):
                    arr = np.array(values, dtype=np.float32)
                    norm = float(np.linalg.norm(arr))
                    if norm > 1e-8:
                        arr = arr / norm
                    return arr.tolist()
            else:
                logger.warning("Gemini embedding returned HTTP %d: %s", resp.status_code, resp.text[:150])
    except Exception as exc:
        logger.warning("Gemini embedding request failed: %s", exc)

    return None


class EmbeddingEngine:
    """
    Configurable embedding engine supporting Gemini embeddings with
    guaranteed deterministic offline fallback.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        fallback_to_local: bool = True,
    ):
        # provider can be 'auto', 'gemini', or 'local'
        env_provider = os.getenv("EMBEDDING_PROVIDER", "auto").lower()
        self.provider = (provider or env_provider).lower()
        self.fallback_to_local = fallback_to_local
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model = os.getenv("GEMINI_EMBEDDING_MODEL", GEMINI_EMBEDDING_MODEL)

    @property
    def dimension(self) -> int:
        if self.provider == "gemini" and self.api_key:
            return 768  # text-embedding-004 dimension
        return DETERMINISTIC_EMBEDDING_DIM

    def embed_text(self, text: str) -> List[float]:
        """Generates an embedding vector for a single text string."""
        if not text or not text.strip():
            dim = self.dimension
            return [0.0] * dim

        if self.provider in {"auto", "gemini"} and self.api_key:
            gemini_vec = generate_gemini_embedding(text, self.api_key, self.model)
            if gemini_vec is not None:
                return gemini_vec
            if not self.fallback_to_local:
                raise RuntimeError("Gemini embedding call failed and local fallback is disabled.")

        return generate_deterministic_embedding(text, DETERMINISTIC_EMBEDDING_DIM)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a batch of text strings."""
        if not texts:
            return []
        return [self.embed_text(t) for t in texts]


# Module-level singleton instance
_DEFAULT_ENGINE: Optional[EmbeddingEngine] = None


def get_embedding_engine() -> EmbeddingEngine:
    """Returns the shared EmbeddingEngine singleton."""
    global _DEFAULT_ENGINE
    if _DEFAULT_ENGINE is None:
        _DEFAULT_ENGINE = EmbeddingEngine()
    return _DEFAULT_ENGINE


def embed_text(text: str) -> List[float]:
    """Convenience helper to embed a single text string."""
    return get_embedding_engine().embed_text(text)


def embed_batch(texts: List[str]) -> List[List[float]]:
    """Convenience helper to embed a list of text strings."""
    return get_embedding_engine().embed_batch(texts)
