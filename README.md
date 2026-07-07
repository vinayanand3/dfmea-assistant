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

This is a Streamlit MVP for creating first-pass BIW sheet metal DFMEA and DVP&R content from component inputs. The current version uses deterministic rules and synthetic engineering logic only. It is intentionally structured so an OpenAI or RAG-backed generation layer can be added later.

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

## Hosting Note

GitHub Pages cannot run this app directly because Streamlit requires a live Python server and GitHub Pages only serves static files. Use GitHub to store the code, then deploy the app with a Streamlit-capable host such as Streamlit Community Cloud, Render, Railway, Hugging Face Spaces, or an internal server.

## Demo Workflow

1. Open the app.
2. Choose one of the example parts from the sidebar or `Component Input` tab.
3. Keep `Show intentional demo gap` enabled in the sidebar for a management demo.
4. Click `Load Selected Part` or `Load Part`.
5. Click `Generate Drafts`.
6. Review RPN, Action Priority, residual risk, action owners, and review status in the DFMEA tab.
7. Review linked Test IDs, validation levels, build phases, execution status, results, and evidence links in the DVP&R tab.
8. Open `Traceability` and click `Check Gaps`.
9. Open `Gaps` to review the dedicated gap analysis and linked lessons learned.
10. Open `Dashboard` to review management KPIs.
11. Open `Export` and download the markdown report or formatted Excel workbook.

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

- `Management Summary`: executive-friendly proof-of-concept summary, demo story, prototype boundary, Action Priority disclaimer, and engineer approval boundary.
- `Dashboard`: management-facing KPIs, coverage scores, explanatory footnotes, and renamed chart legends.
- `Component Input`: original engineer input, program phase, engineer name, generated date, and tool version.
- `DFMEA`: editable draft risk table with review status fields.
- `DVP&R`: validation recommendations with sorted Test IDs, execution fields, status, results, and evidence links.
- `Traceability`: requirement, function, failure mode, and test linkage with coverage score.
- `Gap Analysis`: focused list of missing or partial validation coverage with explicit gap status, AI-recommended closure test, engineer decision, approval status, evidence link, and final closure status.
- `Lessons Learned`: synthetic lessons learned with future RAG citation placeholders.
- `Pilot Metrics`: pilot time-savings and suggestion-quality metrics.
- `Settings`: rating scales, RPN logic, Action Priority logic, coverage scoring, gap status definitions, disclaimers, and dropdown values.
- `Pitch Readiness Checklist`: final review checklist before a management presentation.

## Important Limitations

- This app does not use proprietary company data.
- Outputs are draft engineering suggestions only.
- Severity, occurrence, detection, validation coverage, and release decisions must be reviewed and approved by responsible engineering teams.
- The rule library is intentionally small and should not be treated as complete DFMEA coverage.

## Future Intelligence Layer

The app is designed to add AI later through a generation provider boundary:

```text
Component inputs
  -> rules-based draft
  -> optional OpenAI enrichment
  -> schema validation
  -> editable tables
  -> traceability and export
```

Recommended next steps:

- Add OpenAI structured JSON generation for DFMEA and DVP&R enrichment.
- Add a secure RAG layer over approved internal lessons learned, historical DFMEAs, DVP&Rs, test procedures, and validation reports.
- Require source citations for RAG-backed recommendations.
- Track accepted, edited, and rejected suggestions.
- Add company-standard Excel templates.
- Add authentication, audit trail, and approval workflow for a production version.
