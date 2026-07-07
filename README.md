---
title: Dfmea Assistant
emoji: 🚀
colorFrom: blue
colorTo: red
sdk: streamlit
app_file: app.py
pinned: false
---

# BIW DFMEA-DVP&R AI Assistant

This is a Streamlit MVP for creating first-pass BIW sheet metal DFMEA and DVP&R content from component inputs. Generation is deterministic and rules-based, grounded by a local RAG knowledge layer that cites similar historical engineering records (synthetic demo corpus included). An optional LLM enrichment layer (Anthropic Claude or OpenAI) can be enabled via environment variables — it is off by default, and every output requires engineer review.

## What It Does

- Captures BIW component information.
- Generates an editable DFMEA draft.
- Recommends editable DVP&R validation items.
- Builds risk-to-test traceability.
- Flags missing validation coverage and high-severity gaps.
- Shows synthetic lessons learned.
- Exports CSV, a management dashboard workbook, and markdown report outputs.
- Includes source, RAG citation, reviewer, decision, and notes columns so later OpenAI and RAG suggestions can be tracked.
- Loads example part definitions from separate JSON files under `examples/parts`.

## What's New in MVP-0.6 (Roadmap validation fixes)

- **Roadmap source schema** — DFMEA, DVP&R, and Lessons rows now carry `Source Evidence`, `Source File`, `Source Sheet`, `Source Row`, `Source Chunk ID`, `AI Confidence`, and `Review Status` as first-class columns (existing citation fields kept for compatibility). Fallback rows are explicitly labeled in `Source Evidence`.
- **Optional LLM generation layer (off by default)** — set `RAG_LLM_PROVIDER=anthropic` or `openai` in `.env` to enable a sidebar toggle. Retrieved context goes through the roadmap Phase 7 prompt builder; LLM suggestions are schema-validated, invented chunk IDs are dropped, and rows are appended as clearly-labeled `LLM + RAG` suggestions requiring engineer review. Without a provider the app is fully deterministic.
- **Environment configuration** — `.env.example` with `VECTOR_DB_PATH`, `RAG_TOP_K_*`, `RAG_MIN_SIMILARITY`, provider keys/models, and `RAG_FORCE_FALLBACK_EMBEDDER` for offline/CI runs.
- **Source-aware gap analysis** — four new gap types: DVP&R test without linked DFMEA risk, requirement without linked validation, no source found for high-risk recommendation, and RAG source found but not used.
- **Dashboard RAG KPIs in the export** — the workbook Dashboard sheet now includes the roadmap RAG KPI block (documents indexed, chunks, sources used, grounded rows, fallback rows, high-risk items without evidence, average AI confidence).
- **Knowledge Base UI** — added component type and optional notes fields per the roadmap; `python-docx` added to requirements so DOCX uploads parse.
- **Test suite** — `tests/test_rag.py` (12 tests) covering Excel/DFMEA/DVP&R chunking, metadata, duplicate skipping, retrieval, fallback, prompt building, LLM output validation, and end-to-end export. Run with `pytest tests/ -q`.

## What's New in MVP-0.5 (Local RAG knowledge layer)

- **Knowledge Base tab** — upload engineering documents (.xlsx, .csv, .md, .txt, .pdf, .docx), assign document type and source strength, and index them into a local vector store. Includes a live search preview.
- **Retrieval-grounded citations** — generated DFMEA, DVP&R, and lessons rows are matched against the knowledge base; grounded rows carry a real citation (file, sheet, row, chunk ID, similarity) plus source strength and AI confidence. Unmatched rows are labeled "No RAG source found - rule-based draft".
- **Synthetic demo corpus** — bundled prior-program style DFMEA/DVP&R workbooks, lessons learned, standards excerpts (WS-JOIN-003, TS-COR-021, DIM-BUILD-007), and launch issue reports under `data/knowledge_base/`. Auto-seeded at startup; regenerate with `python scripts/build_synthetic_corpus.py`.
- **Local embeddings** — sentence-transformers `all-MiniLM-L6-v2` (no API key, fully local), with a deterministic hashed bag-of-words fallback so the app still runs offline before the model downloads.
- **Vector store** — lightweight numpy + JSON store implementing the roadmap interface (`add_chunks`, `search`, `delete_collection`, `get_collection_stats`); swappable for ChromaDB/pgvector in production. Duplicate chunks are skipped by content hash.
- **Export + dashboard updates** — new "Knowledge Base Summary" and "Retrieved Sources" workbook sheets, RAG KPIs on the dashboard, and a RAG explanation row in the Management Summary.
- **No LLM required** — this is retrieval-grounded rules mode per the RAG roadmap Phase 1; an LLM enrichment layer (e.g., Claude) can be added behind the same guardrails later.

## What's New in MVP-0.4 (AIAG-VDA alignment + modern UI)

- **P-Diagram tab** — generated parameter diagram (ideal function, input signal, control factors, the five standard noise factor categories, and error states) supporting AIAG-VDA Step 3 function analysis. Error states map to DFMEA failure modes.
- **FMEA header block** — AIAG-VDA planning & preparation identification block (FMEA ID, subject, design responsibility, core team, key dates, revision) shown on the Input tab and exported as its own workbook sheet.
- **Special Characteristic candidates** — YC (potential critical, S 9–10) and SC (potential significant, S 5–8 with elevated occurrence) flags per DFMEA row, with color coding and dropdowns in the Excel export. Final designation stays with the engineer.
- **AP (AIAG-VDA)** — banded implementation of the AIAG-VDA 2019 Action Priority logic (Severity → Occurrence → Detection, not an RPN threshold) alongside the legacy RPN-based priority for comparison.
- **Vehicle-level end effects** — every failure mode now carries an end effect at customer/vehicle level in addition to the local effect.
- **DVP&R test stages and standards** — DV / PV / Virtual-CAE stage classification and synthetic test standard references (e.g., TS-DUR-BIW-014) per validation row.
- **Modern UI** — themed hero header, forest-green/amber design language, styled tabs and metric cards, custom Streamlit theme.

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Notes for first launch:

- The knowledge base auto-seeds itself from the bundled synthetic corpus — no setup needed.
- The first run downloads the sentence-transformers embedding model (~90 MB). Until it is available, the app automatically uses an offline fallback embedder, so everything still works.
- No API key is required. The app is fully local and deterministic by default.

## Configuration (optional)

Copy `.env.example` to `.env` to change defaults. The main settings:

| Variable | Purpose | Default |
|---|---|---|
| `VECTOR_DB_PATH` | Where the vector store persists | `./data/vector_store` |
| `RAG_TOP_K_DFMEA` / `RAG_TOP_K_DVPR` / `RAG_TOP_K_LESSONS` / `RAG_TOP_K_STANDARDS` | Retrieval depth per context group | 5 / 5 / 3 / 3 |
| `RAG_MIN_SIMILARITY` | Below this, a row is labeled "No RAG source found" | 0.30 |
| `RAG_FORCE_FALLBACK_EMBEDDER` | Set `1` to skip the ML model (offline/CI) | off |
| `RAG_LLM_PROVIDER` | `anthropic` or `openai` to enable the LLM layer | empty (disabled) |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | Provider credentials | empty |

## Run the Tests

```bash
pip install pytest
pytest tests/ -q
```

Twelve tests cover document parsing, chunking, metadata, duplicate skipping, retrieval, fallback behavior, prompt building, LLM output validation, and the end-to-end export.

## Hosting Note

GitHub Pages cannot run this app directly because Streamlit requires a live Python server and GitHub Pages only serves static files. Use GitHub to store the code, then deploy the app with a Streamlit-capable host such as Streamlit Community Cloud, Render, Railway, Hugging Face Spaces, or an internal server.

## How to Use the App (Tab by Tab)

1. **Input** — pick one of the example parts from the sidebar (or this tab) and click `Load Selected Part`, or type your own component details. The auto-derived FMEA header (AIAG-VDA planning & preparation block) is shown in the expander. Keep `Show intentional demo gap` enabled in the sidebar for a management demo. Click `Generate Drafts`.
2. **Knowledge Base** — see what the RAG layer knows. The synthetic corpus (prior-program DFMEAs, DVP&Rs, lessons learned, standards) is indexed automatically. Upload your own `.xlsx/.csv/.md/.txt/.pdf/.docx` files with a document type, source strength, component type, and notes, then click `Process files`. Use the search preview to check what would be retrieved. `Clear knowledge base` resets it; `Seed synthetic demo corpus` restores the demo data.
3. **P-Diagram** — review the generated function analysis: ideal function, input signal, control factors, the five noise factor categories, and error states. Each error state should map to a DFMEA failure mode. Fully editable.
4. **DFMEA** — review the draft risk table: S/O/D, RPN, AIAG-VDA Action Priority, YC/SC special-characteristic candidates, vehicle-level end effects, and recommended actions. Grounded rows show their source (file, sheet, row, chunk ID, similarity) in the source columns; ungrounded rows are labeled "No RAG source found - rule-based draft". Edit, add, or delete rows — downstream tabs refresh automatically.
5. **DVP&R** — review recommended validation tests linked to each failure mode, with test stage (DV/PV/Virtual), validation level, build phase, sample size, acceptance criteria, and standard references. Editable like the DFMEA.
6. **Traceability** — every failure mode mapped to its validation tests with a coverage status (Covered / Partial / Proposed / Gap) and coverage score. Click `Check Gaps` after manual edits.
7. **Gaps** — the gap list with AI-proposed closure tests and engineer decision fields. Includes source-aware gap types such as high-severity risks without source evidence and strong knowledge-base matches not used by the draft.
8. **Dashboard** — management KPIs (risk counts, RPN reduction, coverage scores) plus RAG KPIs (documents indexed, grounded rows, fallback rows, average AI confidence).
9. **Export** — download the markdown pilot report or the formatted 15-sheet Excel workbook.

## Optional: Enable the LLM Enrichment Layer

Off by default — the app never calls an external API unless you configure it.

1. Copy `.env.example` to `.env`.
2. Set `RAG_LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY=...` (or `openai` + `OPENAI_API_KEY`).
3. Install the provider package: `pip install anthropic` (or `pip install openai`).
4. Restart the app and enable the sidebar checkbox `Enable LLM enrichment (optional)`.

On the next `Generate Drafts`, retrieved context is sent to the LLM, which may suggest additional failure modes and validation tests. Suggestions are schema-validated, may only cite real retrieved chunk IDs, and are appended as `LLM + RAG` rows with `Review Status = Under Review` — the engineer accepts, edits, or rejects each one.

## Included Example Parts

- Rear Floor Crossmember Reinforcement
- Shock Tower Reinforcement
- Front Rail Reinforcement
- Roof Rail Reinforcement
- Underbody Battery Mounting Bracket

## Adding More Example Parts

Add a new `.json` file under `examples/parts`. The app loads all files in that folder automatically, so you do not need to edit `app.py` when adding another part.

Use this schema:

```json
{
  "component_name": "Example BIW Component",
  "vehicle_area": "Vehicle area",
  "component_category": "Component category",
  "material": "Material",
  "thickness": "Thickness",
  "joining_method": "Joining methods",
  "manufacturing_process": "Manufacturing process",
  "primary_function": "Primary function",
  "interfaces": "Interfaces",
  "load_cases": "Load cases",
  "environmental_exposure": "Environmental exposure",
  "known_design_concerns": "Known concerns",
  "assumptions": "Synthetic demo data only. Final values require engineering review."
}
```

## Management Demo Notes

The sidebar option `Show intentional demo gap` creates a management-friendly before/after story for bracket or fastener pull-out risk. The tool shows the original validation gap, then proposes a specific DVP&R closure test while still requiring engineer approval. Crash validation is always generated for crash/load-path risks.

The Excel workbook includes:

- `Management Summary`: executive-friendly proof-of-concept summary, demo story, RAG knowledge-layer explanation, prototype boundary, Action Priority disclaimer, and engineer approval boundary.
- `Dashboard`: management-facing KPIs, RAG KPIs, coverage scores, explanatory footnotes, and renamed chart legends.
- `FMEA Header`: AIAG-VDA planning & preparation identification block.
- `Component Input`: original engineer input, program phase, engineer name, generated date, and tool version.
- `Knowledge Base Summary`: indexed document/chunk counts, document types, source strength breakdown, embedding model, and store path.
- `Retrieved Sources`: every source retrieved during generation with similarity score, file/sheet/row, chunk ID, preview, and whether it was used in the output.
- `P-Diagram`: the generated function analysis.
- `DFMEA`: editable draft risk table with source evidence and review status fields.
- `DVP&R`: validation recommendations with sorted Test IDs, test stages, execution fields, status, results, evidence links, and source fields.
- `Traceability`: requirement, function, failure mode, and test linkage with coverage score.
- `Gap Analysis`: missing or partial validation coverage plus source-aware gap types, each with gap status, AI-recommended closure test, engineer decision, approval status, evidence link, and final closure status.
- `Lessons Learned`: lessons matched to the generated risks, with source citations where grounded.
- `Pilot Metrics`: pilot time-savings and suggestion-quality metrics.
- `Settings`: rating scales, RPN and AIAG-VDA AP logic, special characteristic logic, coverage scoring, gap status definitions, disclaimers, and dropdown values.
- `Pitch Readiness Checklist`: final review checklist before a management presentation.

## Important Limitations

- This app does not use proprietary company data.
- Outputs are draft engineering suggestions only.
- Severity, occurrence, detection, validation coverage, and release decisions must be reviewed and approved by responsible engineering teams.
- The rule library is intentionally small and should not be treated as complete DFMEA coverage.

## Architecture

```text
Component inputs
  -> local RAG retrieval (knowledge base of DFMEAs, DVP&Rs, lessons, standards)
  -> rules-based draft with source citations
  -> optional LLM enrichment (Claude or OpenAI, schema-validated, off by default)
  -> editable tables with engineer review fields
  -> traceability, source-aware gap analysis, and cited export
```

Remaining production roadmap:

- Secure internal deployment over approved company documents (replacing the synthetic corpus).
- Swap the local vector store for ChromaDB or pgvector at scale.
- Company-standard Excel templates.
- Authentication, audit trail, and formal approval workflow.
- MCP connectors for SharePoint, PLM, and issue tracking (after RAG proves value).
