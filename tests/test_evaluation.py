"""Quality gates for the reproducible RAG benchmark."""

from __future__ import annotations

import os

os.environ["RAG_FORCE_FALLBACK_EMBEDDER"] = "1"

from evaluation.run_benchmark import DEFAULT_BENCHMARK, DEFAULT_CORPUS, evaluate_benchmark, load_benchmark, validate_benchmark


def test_benchmark_is_complete_unique_and_source_auditable():
    benchmark = load_benchmark(DEFAULT_BENCHMARK)
    profile = validate_benchmark(benchmark, DEFAULT_CORPUS)
    assert profile["questions"] == 30
    assert profile["documents"] == 6
    assert sum(profile["question_distribution"].values()) == 30


def test_fallback_benchmark_meets_ci_quality_floor():
    metrics, rows = evaluate_benchmark("fallback")
    assert metrics["questions"] == 30
    assert metrics["semantic_embeddings"] is False
    assert metrics["recall_at_1"] >= 0.90
    assert metrics["recall_at_5"] >= 0.95
    assert metrics["mrr"] >= 0.90
    assert metrics["citation_exact_at_1"] >= 0.80
    assert metrics["distractor_rejection_at_5"] >= 0.95
    assert len(rows) == 30
    assert len({row["id"] for row in rows}) == 30


def test_embedding_status_is_explicit_in_store_stats(tmp_path):
    from rag.embeddings import get_embedder_status
    from rag.store import VectorStore

    status = get_embedder_status()
    stats = VectorStore(tmp_path / "status-store").get_collection_stats()
    assert status["name"] == "hashed-bow-fallback"
    assert status["is_semantic"] is False
    assert status["fallback_reason"]
    assert stats["active_embedding_model"] == status["name"]
    assert stats["semantic_embeddings"] is False
    assert stats["embedding_fallback_reason"]
