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

This is a Streamlit MVP for creating first-pass BIW sheet metal DFMEA and DVP&R content from component inputs. Generation is deterministic and rules-based, grounded by a local RAG knowledge layer that cites similar historical engineering records (synthetic demo corpus included). An optional LLM enrichment layer (Anthropic Claude or OpenAI) can be enabled via environment variables. It is off by default, and every output requires engineer review.

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

- **Roadmap source schema**: DFMEA, DVP&R, and Lessons rows now carry `Source Evidence`, `Source File`, `Source Sheet`, `Source Row`, `Source Chunk ID`, `AI Confidence`, and `Review Status` as first-class columns (existing citation fields kept for compatibility). Fallback rows are explicitly labeled in `Source Evidence`.
- **Optional LLM generation layer (off by default)**: set `RAG_LLM_PROVIDER=anthropic` or `openai` in `.env` to enable a sidebar toggle. Retrieved context goes through the roadmap Phase 7 prompt builder; LLM suggestions are schema-validated, invented chunk IDs are dropped, and rows are appended as clearly-labeled `LLM + RAG` suggestions requiring engineer review. Without a provider the app is fully deterministic.
- **Environment configuration**: `.env.example` with `VECTOR_DB_PATH`, `RAG_TOP_K_*`, `RAG_MIN_SIMILARITY`, provider keys/models, and `RAG_FORCE_FALLBACK_EMBEDDER` for offline/CI runs.
- **Source-aware gap analysis**: four new gap types: DVP&R test without linked DFMEA risk, requirement without linked validation, no source found for high-risk recommendation, and RAG source found but not used.
- **Dashboard RAG KPIs in the export**: the workbook Dashboard sheet now includes the roadmap RAG KPI block (documents indexed, chunks, sources used, grounded rows, fallback rows, high-risk items without evidence, average AI confidence).
- **Knowledge Base UI**: added component type and optional notes fields per the roadmap; `python-docx` added to requirements so DOCX uploads parse.
- **Test suite**: `tests/test_rag.py` (12 tests) covering Excel/DFMEA/DVP&R chunking, metadata, duplicate skipping, retrieval, fallback, prompt building, LLM output validation, and end-to-end export. Run with `pytest tests/ -q`.

## What's New in MVP-0.5 (Local RAG knowledge layer)

- **Knowledge Base tab**: upload engineering documents (.xlsx, .csv, .md, .txt, .pdf, .docx), assign document type and source strength, and index them into a local vector store. Includes a live search preview.
- **Retrieval-grounded citations**: generated DFMEA, DVP&R, and lessons rows are matched against the knowledge base; grounded rows carry a real citation (file, sheet, row, chunk ID, similarity) plus source strength and AI confidence. Unmatched rows are labeled "No RAG source found - rule-based draft".
- **Synthetic demo corpus**: bundled prior-program style DFMEA/DVP&R workbooks, lessons learned, standards excerpts (WS-JOIN-003, TS-COR-021, DIM-BUILD-007), and launch issue reports under `data/knowledge_base/`. Auto-seeded at startup; regenerate with `python scripts/build_synthetic_corpus.py`.
- **Local embeddings**: sentence-transformers `all-MiniLM-L6-v2` (no API key, fully local), with a deterministic hashed bag-of-words fallback so the app still runs offline before the model downloads.
- **Vector store**: lightweight numpy + JSON store implementing the roadmap interface (`add_chunks`, `search`, `delete_collection`, `get_collection_stats`); swappable for ChromaDB/pgvector in production. Duplicate chunks are skipped by content hash.
- **Export + dashboard updates**: new "Knowledge Base Summary" and "Retrieved Sources" workbook sheets, RAG KPIs on the dashboard, and a RAG explanation row in the Management Summary.
- **No LLM required**: this is retrieval-grounded rules mode per the RAG roadmap Phase 1; an LLM enrichment layer (e.g., Claude) can be added behind the same guardrails later.

## What's New in MVP-0.4 (AIAG-VDA alignment + modern UI)

- **P-Diagram tab**: generated parameter diagram (ideal function, input signal, control factors, the five standard noise factor categories, and error states) supporting AIAG-VDA Step 3 function analysis. Error states map to DFMEA failure modes.
- **FMEA header block**: AIAG-VDA planning & preparation identification block (FMEA ID, subject, design responsibility, core team, key dates, revision) shown on the Input tab and exported as its own workbook sheet.
- **Special Characteristic candidates**: YC (potential critical, S 9–10) and SC (potential significant, S 5–8 with elevated occurrence) flags per DFMEA row, with color coding and dropdowns in the Excel export. Final designation stays with the engineer.
- **AP (AIAG-VDA)**: banded implementation of the AIAG-VDA 2019 Action Priority logic (Severity → Occurrence → Detection, not an RPN threshold) alongside the legacy RPN-based priority for comparison.
- **Vehicle-level end effects**: every failure mode now carries an end effect at customer/vehicle level in addition to the local effect.
- **DVP&R test stages and standards**: DV / PV / Virtual-CAE stage classification and synthetic test standard references (e.g., TS-DUR-BIW-014) per validation row.
- **Modern UI**: themed hero header, forest-green/amber design language, styled tabs and metric cards, custom Streamlit theme.

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Notes for first launch:

- The knowledge base auto-seeds itself from the bundled synthetic corpus, so no setup is needed.
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

## Quick Start (2 Minutes)

If you only want to see what the app does:

1. In the left sidebar, pick an example part (e.g. *Rear Floor Crossmember Reinforcement*) and click **Load Selected Part**.
2. Click **Generate Drafts**.
3. Walk the tabs left to right: the app builds a risk analysis (DFMEA), a test plan (DVP&R), a check that every risk has a test (Traceability), a list of problems it found (Gaps), and a summary (Dashboard).
4. Open **Export** and download the Excel workbook. That is the document you would take into a design review.

Everything below explains each tab in plain language: what it shows, how to read it, and what you get out of it.

---

## Plain-Language Glossary

These five terms are enough to understand the whole app:

- **DFMEA** (Design Failure Mode and Effects Analysis): a structured worry list. For a part, it asks: *what could go wrong (failure mode), what would happen if it did (effect), why would it happen (cause), and how bad/likely/hard-to-catch is it?*
- **S / O / D and RPN**: each risk gets three 1–10 scores: **S**everity (how bad), **O**ccurrence (how likely), **D**etection (how hard to catch before the customer sees it; higher is worse). Multiplied together they give the **RPN** (Risk Priority Number, max 1000). Bigger number = bigger worry.
- **Action Priority (AP)**: the modern industry method (AIAG-VDA) for deciding which risks demand action: **H**igh, **M**edium, or **L**ow. It looks at severity first, so a dangerous-but-rare issue is not hidden by a low RPN.
- **DVP&R** (Design Verification Plan and Report): the test plan. For every risk in the DFMEA, it lists which test proves the design is OK, how many samples, what "pass" means, and who runs it.
- **RAG** (Retrieval-Augmented Generation): instead of inventing content, the app first searches a knowledge base of past engineering documents and cites what it found. Think of it as "show your sources."

---

## Tab-by-Tab Guide

### Tab 1: Input - describe the part

**What it is.** The starting point. You tell the app what part you are working on: its name, material, thickness, how it is joined (welds, adhesive), what loads it sees (crash, vibration), and what already worries you.

**How to use it.** Easiest path: load one of the five built-in example parts and click **Generate Drafts**. You can also edit any field first. The app reacts to keywords, so writing "corrosion" in the concerns box will produce corrosion risks and corrosion tests downstream. The *FMEA header* expander shows the document's identity block (ID, responsible engineer, dates), which is the cover page of the analysis.

**What you get.** Nothing visible yet. This tab feeds every other tab. After clicking **Generate Drafts**, all remaining tabs fill in at once.

### Tab 2: Knowledge Base - what the app "remembers"

**What it is.** The app's library of past engineering documents: old risk analyses, old test plans, lessons learned, and standards. When the app drafts anything, it searches this library and cites matches. A demo library of synthetic (fake but realistic) documents is loaded automatically.

**How to read it.** The four boxes at the top show how much the library contains (documents and searchable snippets called "chunks"). The table at the bottom (after a generation) lists exactly which sources the last draft used.

**How to use it.** You can ignore this tab entirely and the app still works. To extend the library: choose a document type (e.g. *Historical DFMEA*), a source strength (how trustworthy it is), optionally the component it relates to and a note, then upload files and click **Process files**. Try the **search preview** box. Type "weld fatigue" and see what the app would find.

**What you get.** Better, source-backed drafts. Rows backed by a library match show exactly which file and row they came from, so a reviewer can check the source instead of trusting the tool.

### Tab 3: P-Diagram - how the part is supposed to work

**What it is.** A one-page description of the part's job: what it should do (*ideal function*), what goes into it (*input signal*: the loads), what the designer controls (*control factors*: material, thickness, welds), what the designer cannot control (*noise factors*: manufacturing variation, aging, rough roads, weather, neighboring parts), and what "going wrong" looks like (*error states*).

**How to read it.** Read the Element column top to bottom; it tells the part's story. The three counters show how many control factors, noise categories, and error states were generated. Every error state should reappear as a risk on the DFMEA tab; that is the link between "how it works" and "how it fails."

**What you get.** The engineering justification for the risk list. In a review, this is how you answer "why did you include that failure mode?"

### Tab 4: DFMEA - the risk list

**What it is.** The core output: one row per thing that could go wrong with the part.

**How to read a row.** Read left to right as a sentence: *this part* (Item) *is supposed to do X* (Function), *but could fail like this* (Potential Failure Mode), *which would cause this* (Effect, and End Effect at the vehicle/customer level), *because of this* (Cause). Then the scores: Severity, Occurrence, Detection, RPN, and **AP (AIAG-VDA)**. If AP says **H**, that row needs attention. A **YC/SC** flag means the row is a candidate safety-critical or significant characteristic. **Recommended Action** says what to do about it; the **Revised** scores estimate the risk after that action.

**Where the sources are.** Scroll right: *Source File / Sheet / Row* and *Source Evidence* show the historical record backing the row. If it says "No RAG source found - rule-based draft," the row came from built-in engineering rules and deserves closer human scrutiny.

**How to use it.** Every cell is editable, and you can add or delete rows. Change a severity score and the downstream tabs recalculate automatically. The **Engineer Decision** column is where a reviewer records Accept / Modify / Reject.

**What you get.** A downloadable draft DFMEA (CSV button below the table) that would normally take an engineer one to two days to assemble from old files.

### Tab 5: DVP&R - the test plan

**What it is.** One row per recommended test, each linked to the risk it covers.

**How to read a row.** *Linked Failure Mode* is the risk being addressed. *Recommended Validation Test* is the test. *Test Stage* says when it happens (Virtual/CAE = computer simulation, DV = design verification on prototypes, PV = production validation on real production parts). *Sample Size*, *Acceptance Criteria*, and *Responsible Team* say how many parts, what counts as passing, and who owns it. Execution columns (dates, actual result, Pass/Fail, evidence link) are blank in a draft; they get filled as the program runs the tests.

**What you get.** A draft validation plan (CSV download) with every test traceable to a specific risk, which is the structure quality auditors look for.

### Tab 6: Traceability - does every risk have a test?

**What it is.** The cross-check between the two previous tabs. Every DFMEA risk appears once, with the tests that cover it.

**How to read it.** The five counters at the top are the summary: how many risks are **Covered** (green in the Excel export), **Partial** (some testing, not enough), or **Gap** (no test at all, shown red). The Coverage Score is the overall percentage. In the table, high-severity rows with anything other than "Covered" are the ones to raise in a review.

**What you get.** The single most important management view: proof that no known risk is silently untested. Click **Check Gaps** after editing other tabs to refresh it.

### Tab 7: Gaps - what the app flagged for humans

**What it is.** The app's findings: the list of problems it wants a human to resolve. This is where the tool goes beyond generating paperwork and starts checking it.

**How to read it.** Each row is one finding. *Gap Type* says what kind: a risk with no test, a proposed test awaiting engineer acceptance, a high-severity risk with no supporting source in the knowledge base, a test pointing at a risk that does not exist, or a strong library match the draft never used. *Priority* High + Severity 8+ = deal with it first. *Recommended Fix* proposes a concrete closure (usually a specific test). A gap stays **Open** until an engineer accepts the fix and links evidence; the app never closes its own findings.

**What you get.** An action list. In the demo, enable "Show intentional demo gap" in the sidebar to see a high-severity gap get caught and a closure test proposed. That moment is the pitch.

**Lessons Learned** (bottom of this tab): advice from past programs that matches the current part's risks, e.g. "P1 crossmember cracked at a 3.5 mm radius; keep radii ≥ 4× thickness." This is how the app stops knowledge from leaving with retiring engineers.

### Tab 8: Dashboard - the summary for management

**What it is.** The numbers that summarize everything: how many risks, how many high-severity, highest RPN, estimated risk reduction if actions are taken, test count, coverage scores, open gaps. Below them, the **RAG knowledge layer** row shows how much of the draft is source-backed: documents indexed, rows with source evidence, rows on rule-based fallback, and average AI confidence.

**How to read it.** Three questions answered at a glance: *How risky is this part?* (risk counts, highest RPN). *Is the plan complete?* (coverage scores; high-severity coverage should be 100%). *Can we trust the draft?* (grounded rows vs fallback rows).

### Tab 9: Export - take the results with you

**What it is.** Two downloads: a markdown pilot report (readable summary) and a formatted Excel workbook (the full engineering document).

**What you get.** The workbook has 15 sheets: management summary first, then dashboard, FMEA header, inputs, knowledge-base summary, retrieved sources, P-Diagram, the editable DFMEA/DVP&R/Traceability/Gap/Lessons tables, pilot metrics, settings (how every score is calculated), and a pitch-readiness checklist. It is color-coded (red = gap/high risk, yellow = partial/medium, green = covered/low), has filters and dropdowns, and is designed to be reviewed by people who never open the app.

---

## Reading the Colors (App and Excel)

- **Red**: needs attention: high Action Priority, high residual risk, or an uncovered risk.
- **Yellow**: in between: medium priority or partial coverage.
- **Green**: healthy: covered risks, low residual risk.
- **"No RAG source found - rule-based draft"**: the row is a reasonable engineering default, not backed by a historical document; review it more carefully.

## Optional: Enable the LLM Enrichment Layer

Off by default. The app never calls an external API unless you configure it.

1. Copy `.env.example` to `.env`.
2. Set `RAG_LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY=...` (or `openai` + `OPENAI_API_KEY`).
3. Install the provider package: `pip install anthropic` (or `pip install openai`).
4. Restart the app and enable the sidebar checkbox `Enable LLM enrichment (optional)`.

On the next `Generate Drafts`, retrieved context is sent to the LLM, which may suggest additional failure modes and validation tests. Suggestions are schema-validated, may only cite real retrieved chunk IDs, and are appended as `LLM + RAG` rows with `Review Status = Under Review`. The engineer accepts, edits, or rejects each one.

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
