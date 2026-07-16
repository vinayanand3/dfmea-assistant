"""Embedding backends for the local RAG layer.

Primary backend: sentence-transformers (all-MiniLM-L6-v2) - real semantic search,
runs fully local, no API key. Fallback backend: a deterministic hashed bag-of-words
embedder (pure numpy) so the app still works offline or before the model downloads.
"""

from __future__ import annotations

import hashlib
import re

import numpy as np

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_FALLBACK_DIM = 512

_embedder_singleton = None
_embedder_error = ""


class HashedBowEmbedder:
    """Deterministic hashed bag-of-words embedder (no ML dependencies).

    Not as strong as a transformer model, but fully offline, instant, and good
    enough to demo retrieval over a few hundred engineering chunks.
    """

    name = "hashed-bow-fallback"
    is_semantic = False

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), _FALLBACK_DIM), dtype=np.float32)
        for i, text in enumerate(texts):
            tokens = re.findall(r"[a-z0-9\-]+", str(text).lower())
            for token in tokens:
                bucket = int(hashlib.md5(token.encode()).hexdigest(), 16) % _FALLBACK_DIM
                vectors[i, bucket] += 1.0
            norm = np.linalg.norm(vectors[i])
            if norm > 0:
                vectors[i] /= norm
        return vectors


class SentenceTransformerEmbedder:
    name = _MODEL_NAME
    is_semantic = True

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(_MODEL_NAME)

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = self._model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(vectors, dtype=np.float32)


def get_embedder():
    """Return the best available embedder, caching the instance."""
    global _embedder_singleton, _embedder_error
    if _embedder_singleton is not None:
        return _embedder_singleton
    from . import config

    if config.RAG_FORCE_FALLBACK_EMBEDDER:
        _embedder_singleton = HashedBowEmbedder()
        _embedder_error = "Fallback explicitly enabled by RAG_FORCE_FALLBACK_EMBEDDER"
        return _embedder_singleton
    try:
        _embedder_singleton = SentenceTransformerEmbedder()
        _embedder_error = ""
    except Exception as exc:
        _embedder_singleton = HashedBowEmbedder()
        _embedder_error = f"{type(exc).__name__}: {exc}"
    return _embedder_singleton


def get_embedder_status() -> dict[str, object]:
    """Return explicit runtime diagnostics for UI, exports, and evaluation."""
    embedder = get_embedder()
    return {
        "name": embedder.name,
        "is_semantic": bool(getattr(embedder, "is_semantic", False)),
        "fallback_reason": _embedder_error if not getattr(embedder, "is_semantic", False) else "",
    }
