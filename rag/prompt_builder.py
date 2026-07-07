"""Prompt builder for LLM-based RAG generation (roadmap Phase 7).

Builds a prompt containing user component input, retrieved context groups,
the rules-based baseline, the required output schema, and safety instructions.
"""

from __future__ import annotations

import json
from typing import Any

OUTPUT_SCHEMA = {
    "dfmea_rows": [
        {
            "failure_mode": "string - potential failure mode",
            "effect": "string - potential effect of failure",
            "cause": "string - potential cause / mechanism",
            "severity": "int 1-10",
            "occurrence": "int 1-10",
            "detection": "int 1-10",
            "prevention_control": "string",
            "detection_control": "string",
            "recommended_action": "string",
            "owner": "string - responsible team",
            "rationale": "string - why this is relevant for this component",
            "source_chunk_ids": ["chunk ids from the retrieved context that support this row; empty list if none"],
        }
    ],
    "dvpr_rows": [
        {
            "linked_failure_mode": "string - must match a failure_mode above or an existing draft row",
            "test": "string - recommended validation test",
            "validation_type": "string - CAE / Physical / Environmental / Manufacturing validation",
            "objective": "string - test objective",
            "acceptance_criteria": "string",
            "team": "string - responsible team",
            "rationale": "string",
            "source_chunk_ids": ["chunk ids from the retrieved context that support this row; empty list if none"],
        }
    ],
}

SAFETY_RULES = """Important rules:
- Do not claim a recommendation is source-grounded unless it is supported by the retrieved context below.
- Only reference chunk IDs that appear in the retrieved context. Never invent chunk IDs, file names, or rows.
- If no source supports a row, return an empty source_chunk_ids list so it is labeled as un-grounded.
- Suggest only rows that ADD to the rules-based baseline (new failure modes, missing tests). Do not repeat baseline rows.
- Severity, occurrence, and detection must be integers from 1 to 10.
- Engineer review is required for all generated content. You do not release or approve engineering content.
- Respond with a single JSON object matching the output schema. No prose, no markdown fences."""


def _format_chunks(chunks: list[dict[str, Any]]) -> str:
    if not chunks:
        return "(none retrieved)"
    blocks = []
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        blocks.append(
            f"[chunk_id: {chunk.get('chunk_id')}] (file: {meta.get('file_name')}, sheet: {meta.get('sheet_name')}, "
            f"row: {meta.get('row_number')}, type: {meta.get('document_type')}, similarity: {chunk.get('similarity')})\n"
            f"{chunk.get('chunk_text', '')}"
        )
    return "\n\n".join(blocks)


def build_rag_prompt(
    inputs: dict[str, str],
    retrieved: dict[str, list[dict[str, Any]]],
    baseline_failure_modes: list[str],
    baseline_tests: list[str],
) -> str:
    component_lines = "\n".join(f"{key}: {value}" for key, value in inputs.items() if value)
    return f"""You are an expert BIW sheet metal DFMEA and DVP&R engineering assistant.

Your task is to enrich a rules-based draft using the user component input and retrieved source context.

{SAFETY_RULES}

User Component Input:
{component_lines}

Rules-Based Baseline Failure Modes (already drafted - do not repeat):
{chr(10).join('- ' + fm for fm in baseline_failure_modes) or '(none)'}

Rules-Based Baseline Validation Tests (already drafted - do not repeat):
{chr(10).join('- ' + t for t in baseline_tests) or '(none)'}

Retrieved DFMEA Context:
{_format_chunks(retrieved.get('dfmea', []))}

Retrieved DVP&R Context:
{_format_chunks(retrieved.get('dvpr', []))}

Retrieved Lessons Learned:
{_format_chunks(retrieved.get('lessons', []))}

Retrieved Standards/Guidelines:
{_format_chunks(retrieved.get('standards', []))}

Generate output as a single JSON object with this schema:
{json.dumps(OUTPUT_SCHEMA, indent=2)}

Return at most 5 dfmea_rows and 5 dvpr_rows. Return empty lists if the retrieved context adds nothing new."""
