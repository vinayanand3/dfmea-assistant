"""Local vector store with JSON + npy persistence.

Implements the interface recommended in the RAG roadmap (add_chunks, search,
delete_collection, get_collection_stats) with a small numpy cosine-similarity
backend. This keeps installs light for Hugging Face Spaces and local demos.
A production version can swap this class for ChromaDB or pgvector unchanged.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .embeddings import get_embedder


def chunk_hash(file_name: str, sheet_name: str, row_number: Any, chunk_text: str) -> str:
    raw = f"{file_name}|{sheet_name}|{row_number}|{chunk_text}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


class VectorStore:
    def __init__(self, path: str | Path = "data/vector_store") -> None:
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self._meta_file = self.path / "chunks.json"
        self._vec_file = self.path / "embeddings.npy"
        self._chunks: list[dict[str, Any]] = []
        self._vectors: np.ndarray | None = None
        self._load()

    # ------------------------------------------------------------- persistence
    def _load(self) -> None:
        if self._meta_file.exists():
            self._chunks = json.loads(self._meta_file.read_text())
        if self._vec_file.exists():
            self._vectors = np.load(self._vec_file)
        if self._vectors is not None and len(self._chunks) != len(self._vectors):
            # corrupted / mismatched state - reset rather than crash the demo
            self._chunks, self._vectors = [], None

    def _save(self) -> None:
        self._meta_file.write_text(json.dumps(self._chunks, ensure_ascii=False))
        if self._vectors is not None:
            np.save(self._vec_file, self._vectors)

    # -------------------------------------------------------------- interface
    def add_chunks(self, chunks: list[dict[str, Any]]) -> int:
        """Embed and store chunks, skipping duplicates by content hash."""
        existing = {c["chunk_id"] for c in self._chunks}
        fresh = [c for c in chunks if c["chunk_id"] not in existing]
        if not fresh:
            return 0
        embedder = get_embedder()
        vectors = embedder.encode([c["chunk_text"] for c in fresh])
        for chunk in fresh:
            chunk.setdefault("metadata", {})
            chunk["metadata"].setdefault("created_at", datetime.now(timezone.utc).isoformat())
            chunk["metadata"]["embedding_model"] = embedder.name
        self._chunks.extend(fresh)
        self._vectors = vectors if self._vectors is None else np.vstack([self._vectors, vectors])
        self._save()
        return len(fresh)

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Cosine-similarity search with optional metadata filters.

        Filter values may be a string (exact match) or list of strings (any match).
        A filter key of 'document_type_contains' does substring matching.
        """
        if self._vectors is None or not self._chunks:
            return []
        query_vec = get_embedder().encode([query])[0]
        scores = self._vectors @ query_vec

        candidates = []
        for idx, chunk in enumerate(self._chunks):
            meta = chunk.get("metadata", {})
            if filters and not _passes(meta, filters):
                continue
            candidates.append((float(scores[idx]), chunk))
        candidates.sort(key=lambda pair: pair[0], reverse=True)

        results = []
        for score, chunk in candidates[:top_k]:
            record = dict(chunk)
            record["similarity"] = round(score, 4)
            results.append(record)
        return results

    def delete_collection(self) -> None:
        self._chunks, self._vectors = [], None
        for file in (self._meta_file, self._vec_file):
            if file.exists():
                file.unlink()

    def get_collection_stats(self) -> dict[str, Any]:
        doc_types: dict[str, int] = {}
        strengths: dict[str, int] = {}
        files = set()
        latest = ""
        for chunk in self._chunks:
            meta = chunk.get("metadata", {})
            doc_types[meta.get("document_type", "Other")] = doc_types.get(meta.get("document_type", "Other"), 0) + 1
            strengths[meta.get("source_strength", "Unknown")] = strengths.get(meta.get("source_strength", "Unknown"), 0) + 1
            files.add(meta.get("file_name", ""))
            latest = max(latest, meta.get("created_at", ""))
        return {
            "documents": len(files - {""}),
            "chunks": len(self._chunks),
            "document_types": doc_types,
            "source_strengths": strengths,
            "last_indexed": latest,
            "embedding_model": get_embedder().name,
            "path": str(self.path),
        }


def _passes(meta: dict[str, Any], filters: dict[str, Any]) -> bool:
    for key, expected in filters.items():
        if key == "document_type_contains":
            if str(expected).lower() not in str(meta.get("document_type", "")).lower():
                return False
        elif isinstance(expected, (list, tuple, set)):
            if meta.get(key) not in expected:
                return False
        elif meta.get(key) != expected:
            return False
    return True
