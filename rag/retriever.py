"""Retrieval helpers: build component queries and grouped retrieval per roadmap."""

from __future__ import annotations

from typing import Any

from . import config
from .store import VectorStore

TOP_K_DFMEA = config.RAG_TOP_K_DFMEA
TOP_K_DVPR = config.RAG_TOP_K_DVPR
TOP_K_LESSONS = config.RAG_TOP_K_LESSONS
TOP_K_STANDARDS = config.RAG_TOP_K_STANDARDS

# Below this cosine similarity a match is treated as "no relevant source found".
MIN_SIMILARITY = config.RAG_MIN_SIMILARITY


def build_component_query(inputs: dict[str, str], extra: str = "") -> str:
    fields = [
        ("Component", inputs.get("component_name")),
        ("Vehicle area", inputs.get("vehicle_area")),
        ("Material", inputs.get("material")),
        ("Thickness", inputs.get("thickness")),
        ("Joining", inputs.get("joining_method")),
        ("Manufacturing", inputs.get("manufacturing_process")),
        ("Function", inputs.get("primary_function")),
        ("Load cases", inputs.get("load_cases")),
        ("Interfaces", inputs.get("interfaces")),
        ("Environment", inputs.get("environmental_exposure")),
        ("Concerns", inputs.get("known_design_concerns")),
    ]
    lines = ["Find similar BIW sheet metal DFMEA and DVP&R engineering records for:"]
    lines += [f"{label}: {value}" for label, value in fields if value]
    if extra:
        lines.append(extra)
    return "\n".join(lines)


def retrieve_groups(store: VectorStore, inputs: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
    """Retrieve DFMEA, DVP&R, lessons, and standards context groups."""
    query = build_component_query(inputs)
    return {
        "dfmea": store.search(query, top_k=TOP_K_DFMEA, filters={"document_type": "Historical DFMEA"}),
        "dvpr": store.search(query, top_k=TOP_K_DVPR, filters={"document_type": "Historical DVP&R"}),
        "lessons": store.search(query, top_k=TOP_K_LESSONS, filters={"document_type": "Lessons Learned"}),
        "standards": store.search(query, top_k=TOP_K_STANDARDS, filters={"document_type_contains": "Standard"}),
    }


def best_match_for_row(
    store: VectorStore,
    row_text: str,
    document_type: str,
) -> dict[str, Any] | None:
    """Find the single best source chunk for one generated row."""
    results = store.search(row_text, top_k=1, filters={"document_type": document_type})
    if results and results[0]["similarity"] >= MIN_SIMILARITY:
        return results[0]
    return None


def citation_label(match: dict[str, Any]) -> str:
    meta = match.get("metadata", {})
    return (
        f"{meta.get('file_name', '?')} | sheet: {meta.get('sheet_name', '?')} | "
        f"row: {meta.get('row_number', '?')} | chunk: {match.get('chunk_id', '?')} | "
        f"similarity: {match.get('similarity', 0):.2f}"
    )
