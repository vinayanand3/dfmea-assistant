# Retrieval Evaluation

## Executive result

The retrieval layer passes the current publication quality gates in both supported embedding modes. On the checked-in 30-question synthetic benchmark, both modes retrieve the expected document within the top three for every question and reject the unrelated distractor from the top five for every question.

These results establish reproducibility for this prototype. They do not establish production performance on proprietary OEM data, unseen terminology, or independently authored queries.

## Dataset quality and scope

| Check | Result |
|---|---:|
| Evaluation questions | 30 |
| Unique question IDs | 30 of 30 |
| Unique queries | 30 of 30 |
| Expected source files present | 30 of 30 |
| Expected markers present in their source | 30 of 30 |
| Explicit forbidden distractor present | 30 of 30 |
| Relevant source documents | 6 |
| Unrelated distractor documents | 1 |

Question distribution by expected source:

| Source | Questions |
|---|---:|
| Historical front-rail DFMEA | 7 |
| Historical front-rail DVP&R | 6 |
| Front-rail and underbody lessons learned | 5 |
| Joining standard | 4 |
| Corrosion standard | 4 |
| Unrelated roof-rail CAE report used as a source-specific retrieval target | 4 |

The benchmark grain is one source-specific engineering question per record in `evaluation/benchmark.json`. Expected relevance is exact-document relevance. Each question also specifies an expected marker that must occur in the expected source and an unrelated infotainment document that should not be retrieved.

## Metric definitions

- **Recall@k**: percentage of questions for which the expected source document appears in the first `k` results.
- **MRR**: mean reciprocal rank of the expected source document. A top-ranked expected source receives 1.0, rank two receives 0.5.
- **Exact citation@1**: percentage for which the first result is the expected source and its retrieved chunk contains the expected marker.
- **Distractor rejection@5**: percentage for which the explicitly unrelated distractor is absent from the first five results.
- **Query latency**: retrieval time measured inside one local process after indexing. It excludes application startup, model download, file upload, and UI rendering.

## Results

| Embedding mode | Recall@1 | Recall@3 | Recall@5 | MRR | Exact citation@1 | Distractor rejection@5 | Average latency | P95 latency | Indexing time |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MiniLM semantic | 93.3% | 100% | 100% | 0.967 | 93.3% | 100% | 7.526 ms | 8.188 ms | 229.207 ms |
| Hashed BOW fallback | 96.7% | 100% | 100% | 0.983 | 86.7% | 100% | 0.072 ms | 0.095 ms | 14.169 ms |

Raw and per-question artifacts:

- `evaluation/results/semantic_metrics.json`
- `evaluation/results/semantic_details.csv`
- `evaluation/results/semantic_summary.md`
- `evaluation/results/fallback_metrics.json`
- `evaluation/results/fallback_details.csv`
- `evaluation/results/fallback_summary.md`

## Interpretation

The fallback retriever has slightly better expected-document ranking on this benchmark. That result is plausible because the controlled corpus and questions share distinctive identifiers and engineering vocabulary, which benefits lexical matching. It should not be interpreted as evidence that lexical retrieval is generally more capable than semantic retrieval.

MiniLM has better exact citation-marker accuracy at rank one. This indicates that it more often selects the specific chunk containing the expected evidence, even when both methods find the correct source document within the first results.

The latency comparison is local and hardware-specific. MiniLM uses a neural embedding model while fallback hashing is a small NumPy operation. The values describe this run, not a hosting service-level objective.

## Automated quality gates

`tests/test_evaluation.py` verifies the benchmark contract and runs the fallback benchmark in CI. Current gates are:

- Recall@1 at least 0.90
- Recall@5 at least 0.95
- MRR at least 0.90
- exact citation@1 at least 0.80
- distractor rejection@5 at least 0.95

The semantic model is intentionally excluded from CI installation to keep pull requests fast and deterministic. Its results can be reproduced locally with the full requirements.

## Reproduction

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m evaluation.run_benchmark --mode semantic
python -m evaluation.run_benchmark --mode fallback
```

To write results elsewhere:

```bash
python -m evaluation.run_benchmark --mode fallback --output-dir /tmp/rag-evaluation
```

The evaluator creates a temporary vector store, indexes the exact files in `evaluation/corpus/` using the application's loader, executes all questions through the application's retriever, validates the benchmark metadata, and writes the aggregate and per-question results.

## Threats to validity

- The dataset is synthetic, small, English-only, and centered on BIW engineering.
- Questions were derived from the corpus by the project author, creating vocabulary and authoring bias.
- Expected relevance is a single exact document even when another source may be technically related.
- The explicit distractor is intentionally unrelated and does not represent a difficult near-neighbor negative set.
- The benchmark evaluates retrieval, not the correctness of generated DFMEA ratings or DVP&R acceptance criteria.
- Optional LLM mode has no answer-level faithfulness, completeness, or citation-entailment benchmark yet.
- No inter-rater agreement study was performed with independent automotive engineers.

## Next evaluation milestone

A stronger pilot evaluation would use independently authored questions, confidential data under proper governance, hard component-level distractors, expert relevance labels, nDCG, answer faithfulness, citation entailment, and task-level measures such as review time saved and high-severity coverage defects found.
