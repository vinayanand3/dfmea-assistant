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
