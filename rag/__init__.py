"""Local RAG layer for the BIW DFMEA-DVP&R AI Assistant.

Retrieval-grounded rules mode: the rules-based generator remains the draft engine,
and this package retrieves similar historical engineering records so each generated
row can carry a real, auditable source citation. No external APIs are required.
"""

from .embeddings import get_embedder, get_embedder_status
from .store import VectorStore, chunk_hash
from .loader import load_file_to_chunks, chunk_dataframe_rows, chunk_text_document
from .retriever import build_component_query, retrieve_groups

__all__ = [
    "get_embedder",
    "get_embedder_status",
    "VectorStore",
    "chunk_hash",
    "load_file_to_chunks",
    "chunk_dataframe_rows",
    "chunk_text_document",
    "build_component_query",
    "retrieve_groups",
]
