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

COMPONENT_PHRASES = (
    "front rail",
    "roof rail",
    "rear floor",
    "b-pillar",
    "underbody battery",
    "shock tower",
    "rocker",
)


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
        "dfmea": ranked_search(store, query, TOP_K_DFMEA, {"document_type": "Historical DFMEA"}),
        "dvpr": ranked_search(store, query, TOP_K_DVPR, {"document_type": "Historical DVP&R"}),
        "lessons": ranked_search(store, query, TOP_K_LESSONS, {"document_type": "Lessons Learned"}),
        "standards": ranked_search(store, query, TOP_K_STANDARDS, {"document_type_contains": "Standard"}),
    }


def best_match_for_row(
    store: VectorStore,
    row_text: str,
    document_type: str,
) -> dict[str, Any] | None:
    """Find the single best source chunk for one generated row."""
    results = ranked_search(store, row_text, 1, {"document_type": document_type})
    if (
        results
        and results[0]["similarity"] >= MIN_SIMILARITY
        and results[0].get("ranking_score", results[0]["similarity"]) >= MIN_SIMILARITY
    ):
        return results[0]
    return None


def ranked_search(
    store: VectorStore,
    query: str,
    top_k: int = 5,
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Search and apply a small component-conflict rerank.

    The deterministic fallback embedder can score explicit negative phrases such
    as "roof rail, not front rail" too highly because it matches the query words.
    Preserve cosine similarity for transparency while using a separate ranking
    score to demote explicit component conflicts.
    """
    candidates = store.search(query, top_k=max(top_k * 3, 10), filters=filters)
    reranked = rerank_component_conflicts(query, candidates)
    return reranked[:top_k]


def rerank_component_conflicts(
    query: str,
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    query_lower = str(query).lower()
    query_components = [phrase for phrase in COMPONENT_PHRASES if phrase in query_lower]
    query_requests_negative_example = any(
        phrase in query_lower
        for phrase in ("irrelevant", "distractor", "unrelated", "negative example")
    )
    requested_document_types: set[str] = set()
    if "dvp&r" in query_lower or "dvpr" in query_lower:
        requested_document_types.add("Historical DVP&R")
    if "dfmea" in query_lower:
        requested_document_types.add("Historical DFMEA")
    if "lesson" in query_lower:
        requested_document_types.add("Lessons Learned")
    if "weld standard" in query_lower:
        requested_document_types.add("Weld Standard")
    if "corrosion standard" in query_lower:
        requested_document_types.add("Corrosion Standard")
    if "design standard" in query_lower:
        requested_document_types.add("BIW Design Standard")
    reranked: list[dict[str, Any]] = []
    for result in results:
        record = dict(result)
        text = str(record.get("chunk_text", "")).lower()
        metadata = record.get("metadata", {})
        component_meta = str(metadata.get("component_name", "")).lower()
        adjustment = 0.0
        if str(metadata.get("document_type", "")) in requested_document_types:
            # An explicit evidence-class request is a stronger signal than
            # incidental token overlap in another engineering document.
            adjustment += 0.25
        if not query_requests_negative_example and any(
            phrase in text
            for phrase in (
                "intentionally unrelated",
                "included as a distractor",
                "unrelated to biw",
            )
        ):
            adjustment -= 0.25
        for component in query_components:
            if f"not {component}" in text or f"unrelated to {component}" in text:
                adjustment -= 0.20
            if component_meta:
                if component in component_meta:
                    adjustment += 0.03
                elif any(other in component_meta for other in COMPONENT_PHRASES if other != component):
                    adjustment -= 0.12
        record["ranking_score"] = round(float(record.get("similarity", 0)) + adjustment, 4)
        reranked.append(record)
    reranked.sort(
        key=lambda record: (float(record.get("ranking_score", 0)), float(record.get("similarity", 0))),
        reverse=True,
    )
    return reranked


def citation_label(match: dict[str, Any]) -> str:
    meta = match.get("metadata", {})
    return (
        f"{meta.get('file_name', '?')} | sheet: {meta.get('sheet_name', '?')} | "
        f"row: {meta.get('row_number', '?')} | chunk: {match.get('chunk_id', '?')} | "
        f"similarity: {match.get('similarity', 0):.2f}"
    )
