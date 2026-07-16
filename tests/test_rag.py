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
from rag.retriever import MIN_SIMILARITY, ranked_search
from rag.store import VectorStore, chunk_hash

KB_DIR = REPO / "data" / "knowledge_base"
RAG_EVAL_DIR = REPO.parent / "rag_test_upload_docs"


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


def test_duplicate_chunks_within_one_batch_are_skipped(store):
    chunks = load_file_to_chunks(KB_DIR / "biw_weld_standard_ws_join_003.md", "Weld Standard", "Synthetic Demo")
    assert chunks
    assert store.add_chunks([chunks[0], chunks[0]]) == 1
    assert store.get_collection_stats()["chunks"] == 1


def test_reupload_replaces_stale_document_classification(store):
    path = RAG_EVAL_DIR / "cae_report_roof_rail_beta.txt"
    wrong = load_file_to_chunks(path, "Other", "Unknown")
    corrected = load_file_to_chunks(path, "CAE Report", "CAE Report")
    assert store.upsert_document(wrong) == 1
    assert store.upsert_document(corrected) == 1
    stats = store.get_collection_stats()
    assert stats["documents"] == 1
    assert stats["chunks"] == 1
    assert stats["document_types"] == {"CAE Report": 1}
    assert stats["source_strengths"] == {"CAE Report": 1}
    assert store.search("roof rail", filters={"document_type": "Other"}) == []
    assert store.search("roof rail", filters={"document_type": "CAE Report"})


def test_missing_embedding_file_is_rebuilt(tmp_path):
    path = tmp_path / "vs"
    original = VectorStore(path)
    chunks = load_file_to_chunks(KB_DIR / "biw_weld_standard_ws_join_003.md", "Weld Standard", "Synthetic Demo")
    original.add_chunks(chunks)
    (path / "embeddings.npy").unlink()
    reloaded = VectorStore(path)
    assert reloaded.search("spot weld pitch")
    assert (path / "embeddings.npy").exists()


def test_blank_query_returns_no_results(store):
    store.add_chunks(load_file_to_chunks(KB_DIR / "biw_weld_standard_ws_join_003.md", "Weld Standard", "Synthetic Demo"))
    assert store.search("   ") == []


def test_retriever_returns_results(store):
    for name, dtype in [("historical_dfmea_biw.xlsx", "Historical DFMEA"), ("historical_dvpr_biw.xlsx", "Historical DVP&R")]:
        store.add_chunks(load_file_to_chunks(KB_DIR / name, dtype, "Synthetic Demo"))
    results = store.search("spot weld fatigue rail flange", top_k=3, filters={"document_type": "Historical DFMEA"})
    assert results
    assert all(r["metadata"]["document_type"] == "Historical DFMEA" for r in results)
    assert results[0]["similarity"] >= results[-1]["similarity"]


def test_question_bank_retrieval_quality(store):
    """Regression gate for Recall@5, MRR, type precision, and the distractor corpus."""
    corpus = [
        ("historical_dfmea_front_rail_alpha.csv", "Historical DFMEA"),
        ("historical_dvpr_front_rail_alpha.csv", "Historical DVP&R"),
        ("lessons_learned_front_rail_and_underbody.md", "Lessons Learned"),
        ("weld_standard_ws_join_017.md", "Weld Standard"),
        ("corrosion_standard_ec_biw_041.md", "Corrosion Standard"),
        ("cae_report_roof_rail_beta.txt", "CAE Report"),
        ("distractor_infotainment_launch_issue.md", "Other"),
    ]
    for name, document_type in corpus:
        store.add_chunks(load_file_to_chunks(RAG_EVAL_DIR / name, document_type, "Synthetic Demo"))

    cases = [
        ("front rail crash load-path folding outside intended crush zone", "Historical DFMEA", "historical_dfmea_front_rail_alpha.csv"),
        ("DVP&R test to close front rail crash load-path folding risk", "Historical DVP&R", "historical_dvpr_front_rail_alpha.csv"),
        ("front rail flange weld pitch", "Weld Standard", "weld_standard_ws_join_017.md"),
        ("corrosion design change front rail closed overlap flange", "Corrosion Standard", "corrosion_standard_ec_biw_041.md"),
        ("service bracket fastener pull-out risk", "Historical DFMEA", "historical_dfmea_front_rail_alpha.csv"),
        ("roof rail gauge question", "CAE Report", "cae_report_roof_rail_beta.txt"),
        ("irrelevant document for BIW risk retrieval", "Other", "distractor_infotainment_launch_issue.md"),
    ]
    reciprocal_ranks = []
    for query, document_type, expected_file in cases:
        results = store.search(query, top_k=5, filters={"document_type": document_type})
        files = [result["metadata"].get("file_name") for result in results]
        assert expected_file in files, f"{expected_file} missed Recall@5 for: {query}"
        reciprocal_ranks.append(1 / (files.index(expected_file) + 1))
        assert all(result["metadata"].get("document_type") == document_type for result in results)

    assert sum(reciprocal_ranks) / len(reciprocal_ranks) >= 0.85


def test_component_conflict_rerank_demotes_roof_rail_for_front_rail_query(store):
    corpus = [
        ("historical_dfmea_front_rail_alpha.csv", "Historical DFMEA"),
        ("lessons_learned_front_rail_and_underbody.md", "Lessons Learned"),
        ("cae_report_roof_rail_beta.txt", "CAE Report"),
    ]
    for name, document_type in corpus:
        store.add_chunks(load_file_to_chunks(RAG_EVAL_DIR / name, document_type, "Synthetic Demo"))
    results = ranked_search(store, "front rail crash folding", top_k=5)
    files = [result["metadata"].get("file_name") for result in results]
    assert files[0] == "historical_dfmea_front_rail_alpha.csv"
    assert files.index("lessons_learned_front_rail_and_underbody.md") < files.index("cae_report_roof_rail_beta.txt")
    roof = next(result for result in results if result["metadata"].get("file_name") == "cae_report_roof_rail_beta.txt")
    assert roof["ranking_score"] < roof["similarity"]


def test_all_type_search_hides_unrelated_distractor_but_can_find_it_explicitly(store):
    corpus = [
        ("historical_dfmea_front_rail_alpha.csv", "Historical DFMEA"),
        ("historical_dvpr_front_rail_alpha.csv", "Historical DVP&R"),
        ("lessons_learned_front_rail_and_underbody.md", "Lessons Learned"),
        ("distractor_infotainment_launch_issue.md", "Other"),
    ]
    for name, document_type in corpus:
        store.add_chunks(load_file_to_chunks(RAG_EVAL_DIR / name, document_type, "Synthetic Demo"))

    results = ranked_search(
        store,
        "What DVP&R test should close the front rail crash load-path folding risk?",
        top_k=10,
    )
    visible = [
        result
        for result in results
        if result["similarity"] >= MIN_SIMILARITY
        and result.get("ranking_score", result["similarity"]) >= MIN_SIMILARITY
    ]
    files = [result["metadata"].get("file_name") for result in visible]
    assert visible[0]["metadata"].get("document_type") == "Historical DVP&R"
    assert "historical_dvpr_front_rail_alpha.csv" in files
    assert "distractor_infotainment_launch_issue.md" not in files

    negative_example_results = ranked_search(
        store,
        "Which uploaded document is irrelevant to BIW risk retrieval?",
        top_k=5,
        filters={"document_type": "Other"},
    )
    assert negative_example_results
    distractor = negative_example_results[0]
    assert distractor["metadata"].get("file_name") == "distractor_infotainment_launch_issue.md"
    assert distractor["ranking_score"] == distractor["similarity"]


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
    assert (g_dvp["Source Chunk ID"].astype(str) != "").sum() > 0, "no DVP&R rows grounded"
    assert not retrieved.empty
    grounded_rows = pd.concat([g_dfmea, g_dvp, g_lessons], ignore_index=True)
    grounded_rows = grounded_rows[grounded_rows["Source Chunk ID"].fillna("").astype(str).ne("")]
    assert not grounded_rows.empty
    assert grounded_rows["Source Row"].map(lambda value: isinstance(value, str)).all()
    assert grounded_rows["AI Confidence"].notna().all()

    fallback_rows = g_dfmea[g_dfmea["Source Chunk ID"].fillna("").astype(str).eq("")]
    if not fallback_rows.empty:
        assert fallback_rows["AI Confidence"].isna().all()

    edited = g_dfmea.head(1).copy()
    edited.loc[:, ["Initial Severity", "Initial Occurrence", "Initial Detection"]] = [9, 4, 5]
    edited.loc[:, ["Severity", "Occurrence", "Detection"]] = [8, 4, 5]
    edited.loc[:, ["Revised Severity", "Revised Occurrence", "Revised Detection"]] = [8, 2, 3]
    recalculated = app.recalculate_dfmea_derived_fields(edited)
    assert recalculated.iloc[0]["Initial RPN"] == 180
    assert recalculated.iloc[0]["RPN"] == 160
    assert recalculated.iloc[0]["Revised RPN"] == 48
    assert recalculated.iloc[0]["RPN Reduction %"] == pytest.approx(0.733)
    assert recalculated.iloc[0]["Action Priority"] == "High"
    assert recalculated.iloc[0]["AP (AIAG-VDA)"] == "H"
    assert recalculated.iloc[0]["Residual Risk Level"] == "Low"

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
