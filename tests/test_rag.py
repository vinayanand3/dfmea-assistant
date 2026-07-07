"""RAG test suite (roadmap Phase 17). Run with: pytest tests/ -q

Uses the deterministic fallback embedder (RAG_FORCE_FALLBACK_EMBEDDER=1) so tests
run offline without downloading the sentence-transformers model.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ["RAG_FORCE_FALLBACK_EMBEDDER"] = "1"

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import pandas as pd
import pytest

from rag.loader import chunk_dataframe_rows, chunk_text_document, load_file_to_chunks
from rag.llm import validate_llm_output
from rag.prompt_builder import build_rag_prompt
from rag.store import VectorStore, chunk_hash

KB_DIR = REPO / "data" / "knowledge_base"


@pytest.fixture()
def store(tmp_path):
    return VectorStore(tmp_path / "vs")


def test_excel_loader_reads_sheets():
    chunks = load_file_to_chunks(KB_DIR / "historical_dfmea_biw.xlsx", "Historical DFMEA", "Synthetic Demo")
    assert len(chunks) >= 10
    assert all(c["metadata"]["sheet_name"] == "DFMEA" for c in chunks)


def test_dfmea_rows_convert_to_chunks():
    df = pd.DataFrame(
        [{"Component": "Front rail", "Failure Mode": "Spot weld fatigue", "Effect": "Joint separation",
          "Cause": "Coarse weld pitch", "Severity": 8, "Risk Category": "Joining / Durability"}]
    ).astype(str)
    chunks = chunk_dataframe_rows(df, "test.xlsx", "DFMEA", "Historical DFMEA", "Synthetic Demo")
    assert len(chunks) == 1
    assert "Spot weld fatigue" in chunks[0]["chunk_text"]


def test_dvpr_rows_convert_to_chunks():
    chunks = load_file_to_chunks(KB_DIR / "historical_dvpr_biw.xlsx", "Historical DVP&R", "Synthetic Demo")
    assert len(chunks) >= 10
    assert any("Recommended Validation Test" in c["chunk_text"] for c in chunks)


def test_metadata_is_preserved():
    chunks = load_file_to_chunks(KB_DIR / "historical_dfmea_biw.xlsx", "Historical DFMEA", "Synthetic Demo")
    meta = chunks[0]["metadata"]
    for key in ("file_name", "sheet_name", "row_number", "document_type", "source_strength",
                "component_name", "failure_mode", "risk_category"):
        assert key in meta
    assert meta["document_type"] == "Historical DFMEA"
    assert meta["row_number"] == 2


def test_duplicate_chunks_are_skipped(store):
    chunks = load_file_to_chunks(KB_DIR / "lessons_learned_biw.xlsx", "Lessons Learned", "Synthetic Demo")
    first = store.add_chunks(chunks)
    second = store.add_chunks(chunks)
    assert first > 0
    assert second == 0
    assert store.get_collection_stats()["chunks"] == first


def test_retriever_returns_results(store):
    for name, dtype in [("historical_dfmea_biw.xlsx", "Historical DFMEA"), ("historical_dvpr_biw.xlsx", "Historical DVP&R")]:
        store.add_chunks(load_file_to_chunks(KB_DIR / name, dtype, "Synthetic Demo"))
    results = store.search("spot weld fatigue rail flange", top_k=3, filters={"document_type": "Historical DFMEA"})
    assert results
    assert all(r["metadata"]["document_type"] == "Historical DFMEA" for r in results)
    assert results[0]["similarity"] >= results[-1]["similarity"]


def test_no_rag_fallback_works(store):
    # empty store must return no results and never raise
    assert store.search("anything", top_k=5) == []
    assert store.get_collection_stats()["chunks"] == 0


def test_text_chunking_with_overlap():
    text = " ".join(f"word{i}" for i in range(600))
    chunks = chunk_text_document(text, "std.md", "Weld Standard", "Engineering Standard")
    assert len(chunks) >= 2
    # overlap: last words of chunk 1 appear in chunk 2
    tail = chunks[0]["chunk_text"].split()[-5:]
    assert all(w in chunks[1]["chunk_text"] for w in tail)


def test_chunk_hash_is_stable():
    assert chunk_hash("f.xlsx", "S1", 2, "text") == chunk_hash("f.xlsx", "S1", 2, "text")
    assert chunk_hash("f.xlsx", "S1", 2, "text") != chunk_hash("f.xlsx", "S1", 3, "text")


def test_prompt_builder_includes_context_and_rules():
    prompt = build_rag_prompt(
        {"component_name": "Front rail"},
        {"dfmea": [{"chunk_id": "C1", "chunk_text": "FM record", "similarity": 0.8, "metadata": {"file_name": "a.xlsx"}}],
         "dvpr": [], "lessons": [], "standards": []},
        ["Fatigue crack"],
        ["Durability test"],
    )
    assert "C1" in prompt and "Front rail" in prompt
    assert "Never invent chunk IDs" in prompt
    assert "Fatigue crack" in prompt  # baseline not to be repeated


def test_llm_output_validation_rejects_bad_rows():
    payload = {
        "dfmea_rows": [
            {"failure_mode": "Valid", "effect": "E", "cause": "C", "severity": 8, "occurrence": 3,
             "detection": 4, "recommended_action": "A", "source_chunk_ids": ["REAL", "FAKE"]},
            {"failure_mode": "Bad ratings", "effect": "E", "cause": "C", "severity": 99, "occurrence": 3,
             "detection": 4, "recommended_action": "A", "source_chunk_ids": []},
            {"failure_mode": "", "effect": "E", "cause": "C", "severity": 5, "occurrence": 3,
             "detection": 4, "recommended_action": "A"},
        ],
        "dvpr_rows": [{"linked_failure_mode": "Valid", "test": "T", "objective": "O", "acceptance_criteria": "AC"}],
    }
    dfmea, dvpr, notes = validate_llm_output(payload, known_chunk_ids={"REAL"})
    assert len(dfmea) == 1  # two rejected
    assert dfmea[0]["source_chunk_ids"] == ["REAL"]  # invented id dropped
    assert len(dvpr) == 1
    assert any("rejected" in n for n in notes)
    assert any("invented" in n for n in notes)


def test_app_generation_has_source_fields_and_gap_analysis(tmp_path):
    """End-to-end: generation produces roadmap source fields; gap analysis flags high-risk items."""
    os.environ["VECTOR_DB_PATH"] = str(tmp_path / "vs")
    sys.argv = ["app.py"]
    import importlib
    import app as app_module
    app = importlib.reload(app_module)

    inputs = json.loads((REPO / "examples" / "parts" / "rear_floor_crossmember_reinforcement.json").read_text())
    inputs = {k: str(v) for k, v in inputs.items()}
    dfmea = app.generate_dfmea(inputs)
    dvp = app.generate_dvp(dfmea, {"demo_gap_mode": True})
    lessons = app.generate_lessons(dfmea)

    for col in ("Source Evidence", "Source File", "Source Sheet", "Source Row", "Source Chunk ID", "AI Confidence", "Review Status"):
        assert col in dfmea.columns, f"DFMEA missing {col}"
        assert col in dvp.columns, f"DVP&R missing {col}"
        assert col in lessons.columns, f"Lessons missing {col}"

    store = app.get_rag_store()
    app.seed_knowledge_base(store)
    g_dfmea, g_dvp, g_lessons, retrieved = app.ground_with_rag(dfmea, dvp, lessons, inputs)
    assert (g_dfmea["Source Chunk ID"].astype(str) != "").sum() > 0, "no DFMEA rows grounded"
    assert not retrieved.empty

    trace = app.generate_traceability(g_dfmea, g_dvp)
    gaps = app.generate_gap_analysis(trace)
    gaps = app.augment_gap_analysis(gaps, g_dfmea, g_dvp, retrieved)
    assert "Gap Type" in gaps.columns

    tables = app.workbook_tables(inputs, g_dfmea, g_dvp, trace, gaps, g_lessons)
    assert "Knowledge Base Summary" in tables and "Retrieved Sources" in tables
    xlsx = app.workbook_bytes(tables)
    assert len(xlsx) > 10000
    dash = tables["Dashboard"]
    assert (dash["Section"] == "RAG KPI").any(), "Dashboard sheet missing RAG KPIs"
