"""Optional LLM generation layer (roadmap Phases 7-8), off by default.

Provider is selected with RAG_LLM_PROVIDER=anthropic|openai (env or .env).
Without a configured provider the app runs in retrieval-grounded rules mode.
All LLM output is schema-validated; invalid rows and invented chunk IDs are dropped.
"""

from __future__ import annotations

import json
from typing import Any

from . import config


def llm_status() -> tuple[bool, str]:
    """Return (available, human-readable status)."""
    provider = config.RAG_LLM_PROVIDER
    if not provider:
        return False, "Disabled (set RAG_LLM_PROVIDER=anthropic or openai in .env)"
    if provider == "anthropic":
        if not config.ANTHROPIC_API_KEY:
            return False, "RAG_LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is missing"
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False, "anthropic package not installed (pip install anthropic)"
        return True, f"Anthropic Claude ({config.ANTHROPIC_MODEL})"
    if provider == "openai":
        if not config.OPENAI_API_KEY:
            return False, "RAG_LLM_PROVIDER=openai but OPENAI_API_KEY is missing"
        try:
            import openai  # noqa: F401
        except ImportError:
            return False, "openai package not installed (pip install openai)"
        return True, f"OpenAI ({config.OPENAI_MODEL})"
    return False, f"Unknown provider '{provider}'"


def _call_anthropic(prompt: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=config.LLM_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if getattr(block, "type", "") == "text")


def _call_openai(prompt: str) -> str:
    import openai

    kwargs: dict[str, Any] = {"api_key": config.OPENAI_API_KEY}
    if config.OPENAI_BASE_URL:
        kwargs["base_url"] = config.OPENAI_BASE_URL
    client = openai.OpenAI(**kwargs)
    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        max_tokens=config.LLM_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}


def _valid_rating(value: Any) -> bool:
    try:
        return 1 <= int(value) <= 10
    except (TypeError, ValueError):
        return False


def validate_llm_output(
    payload: dict[str, Any],
    known_chunk_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Schema-validate LLM rows. Returns (dfmea_rows, dvpr_rows, rejection_notes)."""
    notes: list[str] = []
    dfmea_rows: list[dict[str, Any]] = []
    for i, row in enumerate(payload.get("dfmea_rows", [])[:5]):
        required = ["failure_mode", "effect", "cause", "severity", "occurrence", "detection", "recommended_action"]
        if not isinstance(row, dict) or any(not str(row.get(k, "")).strip() for k in required):
            notes.append(f"dfmea_rows[{i}]: missing required fields - rejected")
            continue
        if not all(_valid_rating(row.get(k)) for k in ("severity", "occurrence", "detection")):
            notes.append(f"dfmea_rows[{i}]: S/O/D out of range - rejected")
            continue
        cited = [c for c in row.get("source_chunk_ids", []) if c in known_chunk_ids]
        invented = [c for c in row.get("source_chunk_ids", []) if c not in known_chunk_ids]
        if invented:
            notes.append(f"dfmea_rows[{i}]: dropped invented chunk ids {invented}")
        row["source_chunk_ids"] = cited
        dfmea_rows.append(row)
    dvpr_rows: list[dict[str, Any]] = []
    for i, row in enumerate(payload.get("dvpr_rows", [])[:5]):
        required = ["linked_failure_mode", "test", "objective", "acceptance_criteria"]
        if not isinstance(row, dict) or any(not str(row.get(k, "")).strip() for k in required):
            notes.append(f"dvpr_rows[{i}]: missing required fields - rejected")
            continue
        cited = [c for c in row.get("source_chunk_ids", []) if c in known_chunk_ids]
        invented = [c for c in row.get("source_chunk_ids", []) if c not in known_chunk_ids]
        if invented:
            notes.append(f"dvpr_rows[{i}]: dropped invented chunk ids {invented}")
        row["source_chunk_ids"] = cited
        dvpr_rows.append(row)
    return dfmea_rows, dvpr_rows, notes


def generate_llm_enrichment(
    prompt: str,
    known_chunk_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Call the configured provider and return schema-validated enrichment rows."""
    available, status = llm_status()
    if not available:
        return [], [], [f"LLM unavailable: {status}"]
    try:
        raw = _call_anthropic(prompt) if config.RAG_LLM_PROVIDER == "anthropic" else _call_openai(prompt)
    except Exception as exc:
        return [], [], [f"LLM call failed: {exc}"]
    payload = _parse_json(raw)
    if not payload:
        return [], [], ["LLM response was not valid JSON - all rows rejected"]
    return validate_llm_output(payload, known_chunk_ids)
