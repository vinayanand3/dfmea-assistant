"""Run the source-specific RAG retrieval benchmark.

Examples:
    python -m evaluation.run_benchmark --mode fallback
    python -m evaluation.run_benchmark --mode semantic
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import statistics
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

from rag import config
from rag import embeddings
from rag.loader import load_file_to_chunks
from rag.retriever import ranked_search
from rag.store import VectorStore

ROOT = Path(__file__).resolve().parent
DEFAULT_BENCHMARK = ROOT / "benchmark.json"
DEFAULT_CORPUS = ROOT / "corpus"
DEFAULT_RESULTS = ROOT / "results"

DOCUMENT_TYPES = {
    "historical_dfmea_front_rail_alpha.csv": "Historical DFMEA",
    "historical_dvpr_front_rail_alpha.csv": "Historical DVP&R",
    "lessons_learned_front_rail_and_underbody.md": "Lessons Learned",
    "weld_standard_ws_join_017.md": "Weld Standard",
    "corrosion_standard_ec_biw_041.md": "Corrosion Standard",
    "cae_report_roof_rail_beta.txt": "CAE Report",
    "distractor_infotainment_launch_issue.md": "Other",
}


def load_benchmark(path: Path = DEFAULT_BENCHMARK) -> dict[str, Any]:
    return json.loads(path.read_text())


def validate_benchmark(benchmark: dict[str, Any], corpus_dir: Path = DEFAULT_CORPUS) -> dict[str, Any]:
    questions = benchmark.get("questions", [])
    ids = [str(item.get("id", "")).strip() for item in questions]
    normalized_queries = [" ".join(str(item.get("query", "")).lower().split()) for item in questions]
    errors: list[str] = []
    if len(questions) != 30:
        errors.append(f"Expected 30 questions, found {len(questions)}")
    if len(ids) != len(set(ids)):
        errors.append("Question IDs are not unique")
    if len(normalized_queries) != len(set(normalized_queries)):
        errors.append("Benchmark queries are not unique after normalization")
    for item in questions:
        question_id = item.get("id", "unknown")
        expected = corpus_dir / str(item.get("expected_document", ""))
        marker = str(item.get("expected_marker", "")).strip()
        if not str(item.get("query", "")).strip():
            errors.append(f"{question_id}: query is blank")
        if not expected.exists():
            errors.append(f"{question_id}: expected document does not exist: {expected.name}")
        elif marker not in expected.read_text():
            errors.append(f"{question_id}: marker {marker!r} is absent from {expected.name}")
        for forbidden in item.get("forbidden_documents", []):
            forbidden_path = corpus_dir / forbidden
            if not forbidden_path.exists():
                errors.append(f"{question_id}: forbidden document does not exist: {forbidden}")
            if forbidden == expected.name:
                errors.append(f"{question_id}: expected document is also forbidden")
    if errors:
        raise ValueError("Invalid benchmark:\n- " + "\n- ".join(errors))
    return {
        "questions": len(questions),
        "documents": len({item["expected_document"] for item in questions}),
        "question_distribution": dict(Counter(item["expected_document"] for item in questions)),
    }


def configure_embedder(mode: str) -> str:
    embeddings._embedder_singleton = None
    if mode == "fallback":
        config.RAG_FORCE_FALLBACK_EMBEDDER = True
    elif mode == "semantic":
        config.RAG_FORCE_FALLBACK_EMBEDDER = False
        embeddings._embedder_singleton = embeddings.SentenceTransformerEmbedder()
        embeddings._embedder_error = ""
    elif mode == "auto":
        config.RAG_FORCE_FALLBACK_EMBEDDER = False
    else:
        raise ValueError(f"Unsupported mode: {mode}")
    return embeddings.get_embedder().name


def build_store(corpus_dir: Path, store_dir: Path) -> VectorStore:
    store = VectorStore(store_dir)
    for file_name, document_type in DOCUMENT_TYPES.items():
        chunks = load_file_to_chunks(corpus_dir / file_name, document_type, "Synthetic Demo")
        store.upsert_document(chunks)
    return store


def evaluate_benchmark(
    mode: str,
    benchmark_path: Path = DEFAULT_BENCHMARK,
    corpus_dir: Path = DEFAULT_CORPUS,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    benchmark = load_benchmark(benchmark_path)
    profile = validate_benchmark(benchmark, corpus_dir)
    model_name = configure_embedder(mode)
    temp_dir = Path(tempfile.mkdtemp(prefix=f"rag-eval-{mode}-"))
    try:
        index_start = time.perf_counter()
        store = build_store(corpus_dir, temp_dir)
        indexing_ms = (time.perf_counter() - index_start) * 1000
        rows: list[dict[str, Any]] = []
        for item in benchmark["questions"]:
            started = time.perf_counter()
            results = ranked_search(store, item["query"], top_k=5)
            latency_ms = (time.perf_counter() - started) * 1000
            documents = [str(result.get("metadata", {}).get("file_name", "")) for result in results]
            expected_document = item["expected_document"]
            rank = documents.index(expected_document) + 1 if expected_document in documents else None
            top1 = results[0] if results else {}
            top1_document = str(top1.get("metadata", {}).get("file_name", ""))
            top1_text = str(top1.get("chunk_text", ""))
            marker_correct = top1_document == expected_document and item["expected_marker"] in top1_text
            forbidden = set(item.get("forbidden_documents", []))
            distractor_rejected = not any(document in forbidden for document in documents)
            rows.append(
                {
                    "id": item["id"],
                    "query": item["query"],
                    "expected_document": expected_document,
                    "expected_marker": item["expected_marker"],
                    "rank": rank or "",
                    "recall_at_1": int(rank == 1),
                    "recall_at_3": int(rank is not None and rank <= 3),
                    "recall_at_5": int(rank is not None and rank <= 5),
                    "reciprocal_rank": 1 / rank if rank else 0,
                    "citation_exact_at_1": int(marker_correct),
                    "distractor_rejected_at_5": int(distractor_rejected),
                    "latency_ms": round(latency_ms, 3),
                    "top1_document": top1_document,
                    "top1_similarity": top1.get("similarity", ""),
                    "top5_documents": " | ".join(documents),
                }
            )
        count = len(rows)
        latencies = [float(row["latency_ms"]) for row in rows]
        metrics = {
            "benchmark": benchmark["name"],
            "benchmark_version": benchmark["version"],
            "mode_requested": mode,
            "embedding_model": model_name,
            "semantic_embeddings": bool(getattr(embeddings.get_embedder(), "is_semantic", False)),
            "questions": count,
            "documents": profile["documents"],
            "corpus_chunks": store.get_collection_stats()["chunks"],
            "recall_at_1": round(sum(row["recall_at_1"] for row in rows) / count, 4),
            "recall_at_3": round(sum(row["recall_at_3"] for row in rows) / count, 4),
            "recall_at_5": round(sum(row["recall_at_5"] for row in rows) / count, 4),
            "mrr": round(sum(row["reciprocal_rank"] for row in rows) / count, 4),
            "citation_exact_at_1": round(sum(row["citation_exact_at_1"] for row in rows) / count, 4),
            "distractor_rejection_at_5": round(sum(row["distractor_rejected_at_5"] for row in rows) / count, 4),
            "average_latency_ms": round(statistics.mean(latencies), 3),
            "p95_latency_ms": round(sorted(latencies)[max(0, int(0.95 * count) - 1)], 3),
            "indexing_ms": round(indexing_ms, 3),
            "question_distribution": profile["question_distribution"],
        }
        return metrics, rows
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def write_results(metrics: dict[str, Any], rows: list[dict[str, Any]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    mode = str(metrics["mode_requested"])
    (output_dir / f"{mode}_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    with (output_dir / f"{mode}_details.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    summary = [
        f"# RAG Evaluation: {mode.title()} Mode",
        "",
        f"- Embedding model: `{metrics['embedding_model']}`",
        f"- Semantic embeddings: `{metrics['semantic_embeddings']}`",
        f"- Questions: {metrics['questions']}",
        f"- Recall@1: {metrics['recall_at_1']:.1%}",
        f"- Recall@3: {metrics['recall_at_3']:.1%}",
        f"- Recall@5: {metrics['recall_at_5']:.1%}",
        f"- MRR: {metrics['mrr']:.3f}",
        f"- Citation exactness@1: {metrics['citation_exact_at_1']:.1%}",
        f"- Distractor rejection@5: {metrics['distractor_rejection_at_5']:.1%}",
        f"- Average query latency: {metrics['average_latency_ms']:.1f} ms",
        f"- P95 query latency: {metrics['p95_latency_ms']:.1f} ms",
        "",
        "These metrics are measured on a small synthetic, source-specific benchmark and are not production accuracy claims.",
    ]
    (output_dir / f"{mode}_summary.md").write_text("\n".join(summary) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("fallback", "semantic", "auto"), default="fallback")
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_RESULTS)
    args = parser.parse_args()
    metrics, rows = evaluate_benchmark(args.mode, args.benchmark, args.corpus)
    write_results(metrics, rows, args.output_dir)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
