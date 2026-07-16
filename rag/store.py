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
            try:
                self._chunks = json.loads(self._meta_file.read_text())
            except (OSError, json.JSONDecodeError):
                self._chunks = []
        if self._vec_file.exists():
            try:
                self._vectors = np.load(self._vec_file)
            except (OSError, ValueError):
                self._vectors = None
        if self._vectors is not None and len(self._chunks) != len(self._vectors):
            # Preserve readable metadata and rebuild embeddings on the next operation.
            self._vectors = None

    def _save(self) -> None:
        self._meta_file.write_text(json.dumps(self._chunks, ensure_ascii=False))
        if self._vectors is not None:
            np.save(self._vec_file, self._vectors)

    # -------------------------------------------------------------- interface
    def add_chunks(self, chunks: list[dict[str, Any]]) -> int:
        """Embed and store chunks, skipping duplicates by content hash."""
        existing = {c["chunk_id"] for c in self._chunks}
        fresh = []
        for chunk in chunks:
            if chunk["chunk_id"] in existing:
                continue
            existing.add(chunk["chunk_id"])
            fresh.append(chunk)
        if not fresh:
            return 0
        embedder = get_embedder()
        self._ensure_embeddings(embedder)
        vectors = embedder.encode([c["chunk_text"] for c in fresh])
        for chunk in fresh:
            chunk.setdefault("metadata", {})
            chunk["metadata"].setdefault("created_at", datetime.now(timezone.utc).isoformat())
            chunk["metadata"]["embedding_model"] = embedder.name
        self._chunks.extend(fresh)
        self._vectors = vectors if self._vectors is None else np.vstack([self._vectors, vectors])
        self._save()
        return len(fresh)

    def upsert_document(self, chunks: list[dict[str, Any]]) -> int:
        """Add a document or replace its prior chunks when classification/content changes.

        A repeated identical upload remains a no-op. Re-uploading the same file with a
        corrected document type, source strength, component hint, notes, or content
        replaces the stale copy instead of being silently skipped or duplicated.
        """
        if not chunks:
            return 0
        file_names = {str(chunk.get("metadata", {}).get("file_name", "")) for chunk in chunks}
        file_names.discard("")
        if len(file_names) != 1:
            raise ValueError("upsert_document requires chunks from exactly one source file")
        file_name = next(iter(file_names))
        existing_indices = [
            idx
            for idx, chunk in enumerate(self._chunks)
            if str(chunk.get("metadata", {}).get("file_name", "")) == file_name
        ]
        existing_chunks = [self._chunks[idx] for idx in existing_indices]
        if _equivalent_document(existing_chunks, chunks):
            return 0
        old_chunks = self._chunks
        old_vectors = self._vectors
        try:
            if existing_indices:
                remove = set(existing_indices)
                keep = [idx for idx in range(len(self._chunks)) if idx not in remove]
                self._chunks = [self._chunks[idx] for idx in keep]
                if self._vectors is not None:
                    self._vectors = self._vectors[keep] if keep else None
            return self.add_chunks(chunks)
        except Exception:
            self._chunks = old_chunks
            self._vectors = old_vectors
            raise

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
        if not self._chunks:
            return []
        if not str(query).strip():
            return []
        embedder = get_embedder()
        self._ensure_embeddings(embedder)
        if self._vectors is None:
            return []
        query_vec = embedder.encode([query])[0]
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
        stored_models = {
            str(chunk.get("metadata", {}).get("embedding_model", "")).strip()
            for chunk in self._chunks
            if str(chunk.get("metadata", {}).get("embedding_model", "")).strip()
        }
        embedding_model = ", ".join(sorted(stored_models)) if stored_models else get_embedder().name
        return {
            "documents": len(files - {""}),
            "chunks": len(self._chunks),
            "document_types": doc_types,
            "source_strengths": strengths,
            "last_indexed": latest,
            "embedding_model": embedding_model,
            "path": str(self.path),
        }

    def _ensure_embeddings(self, embedder: Any) -> None:
        """Rebuild missing, corrupt, or model-incompatible vectors in place."""
        if not self._chunks:
            self._vectors = None
            return
        stored_models = {
            str(chunk.get("metadata", {}).get("embedding_model", ""))
            for chunk in self._chunks
        }
        needs_rebuild = (
            self._vectors is None
            or len(self._vectors) != len(self._chunks)
            or stored_models != {embedder.name}
        )
        if not needs_rebuild:
            return
        self._vectors = embedder.encode([chunk["chunk_text"] for chunk in self._chunks])
        for chunk in self._chunks:
            chunk.setdefault("metadata", {})["embedding_model"] = embedder.name
        self._save()


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


def _equivalent_document(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> bool:
    if len(existing) != len(incoming):
        return False
    existing_by_id = {chunk.get("chunk_id"): chunk for chunk in existing}
    incoming_by_id = {chunk.get("chunk_id"): chunk for chunk in incoming}
    if set(existing_by_id) != set(incoming_by_id):
        return False
    ignored_metadata = {"created_at", "embedding_model"}
    for chunk_id, incoming_chunk in incoming_by_id.items():
        existing_chunk = existing_by_id[chunk_id]
        if existing_chunk.get("chunk_text") != incoming_chunk.get("chunk_text"):
            return False
        existing_meta = {
            key: value
            for key, value in existing_chunk.get("metadata", {}).items()
            if key not in ignored_metadata
        }
        incoming_meta = {
            key: value
            for key, value in incoming_chunk.get("metadata", {}).items()
            if key not in ignored_metadata
        }
        if existing_meta != incoming_meta:
            return False
    return True
