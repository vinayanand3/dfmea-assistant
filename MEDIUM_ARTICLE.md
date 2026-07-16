# From Automotive Engineer to AI Engineer: Building an Evaluated RAG Assistant for DFMEA and DVP&R

For most of my career, I have worked with automotive engineering problems where mistakes are expensive, traceability matters, and every decision must survive technical review.

That background shaped how I approached my transition into AI engineering.

I did not want to build another generic chatbot that could answer questions about uploaded PDFs. I wanted to build something grounded in a real engineering workflow, with measurable retrieval performance, explicit limitations, and human approval built into the design.

The result is the **BIW DFMEA and DVP&R AI Assistant**, a public Streamlit prototype that combines automotive Body-in-White engineering knowledge with retrieval-augmented generation, deterministic domain logic, traceability, and optional LLM enrichment.

Live application: https://huggingface.co/spaces/vinayanand2/dfmea-assistant

Source code: https://github.com/vinayanand3/dfmea-assistant



**[SCREENSHOT 1: Add a clean image of the application landing page here]**



## The engineering problem I wanted to solve

A DFMEA, or Design Failure Mode and Effects Analysis, is a structured method for identifying how a design could fail, what the effects would be, why the failure could happen, and what actions are needed to reduce risk.

A DVP&R, or Design Verification Plan and Report, defines how those risks and requirements will be validated.

In a real vehicle program, engineers rarely begin with a blank sheet. They search historical DFMEAs, validation plans, standards, CAE reports, launch issues, and lessons learned. The information may exist, but it is often fragmented across files, programs, teams, and naming conventions.

That creates several problems:

- Relevant historical knowledge can be difficult to find.
- Failure modes may be copied without understanding their original context.
- Validation tests may not be traceable to specific risks or requirements.
- High-severity risks can remain weakly supported by source evidence.
- Engineers spend significant time assembling and checking documents manually.

I saw an opportunity for AI, but also a major risk. A free-form language model can generate plausible engineering text without reliable evidence. In a safety-related workflow, plausible is not sufficient.

So I designed the application around a different principle:

> AI should help retrieve evidence, organize reasoning, and identify gaps. It should not silently become the engineering authority.

## Why I chose a hybrid AI architecture

The application is not purely generative. It combines several layers:

1. **Deterministic engineering rules** create the baseline DFMEA and DVP&R structure.
2. **Retrieval** searches historical records, standards, and lessons learned.
3. **Metadata and citations** attach the source file, sheet, row, chunk ID, and similarity to generated rows.
4. **Traceability logic** connects functions, requirements, failure modes, actions, and validation tests.
5. **Gap detection** identifies missing validation, unsupported high-risk recommendations, and strong retrieved sources that were not used.
6. **Optional LLM enrichment** can propose additional rows, but only through schema validation and real retrieved citation IDs.
7. **Human review** remains mandatory for ratings, requirements, acceptance criteria, approval, and release.



**[SCREENSHOT 2: Add the architecture diagram from ARCHITECTURE.md here]**



This architecture was important because DFMEA is not simply a text-generation problem. It is a structured reasoning and traceability problem.

## Building the retrieval pipeline

The application accepts XLSX, CSV, PDF, DOCX, Markdown, and text files.

Spreadsheet rows are treated as complete engineering records. For example, one historical DFMEA row becomes one retrieval chunk instead of being arbitrarily split in the middle of a failure mode. The loader preserves metadata such as:

- document type;
- source file;
- worksheet;
- row number;
- component name;
- failure mode ID;
- requirement ID;
- test ID;
- risk category;
- source strength.

Text documents use bounded chunks with overlap. Explicit labels such as `Component:`, `Risk Category:`, and `Requirement ID:` are extracted into metadata so the reranker can recognize component conflicts.

The default embedding model is `sentence-transformers/all-MiniLM-L6-v2`. It runs locally and does not require an API key.

I also implemented a deterministic hashed bag-of-words fallback for offline development and CI. This fallback is useful, but it is lexical retrieval, not semantic retrieval. The application now states the active mode clearly instead of presenting both modes as equivalent.



**[SCREENSHOT 3: Add the Knowledge Base screen showing “Embedding: Semantic” and the MiniLM model name here]**



The local vector store uses NumPy cosine similarity and JSON metadata. Content hashes prevent duplicate chunks. Document-type filters narrow searches, and a component-conflict reranker demotes evidence from the wrong component when the query clearly identifies a component such as a front rail or roof rail.

## Making the evidence visible

One lesson from building the first version was that retrieval cannot remain hidden behind a similarity table.

If a user sees only a truncated preview, important fields may appear to be missing even when they exist in the stored chunk. That makes the system difficult to trust and difficult to test.

I added an expandable **View full retrieved record** section beneath the search results. It shows:

- retrieval rank;
- similarity;
- document type;
- source file;
- sheet and row;
- source strength;
- chunk ID;
- the complete retrieved engineering record.



**[SCREENSHOT 4: Add the search for “front rail crash folding” with the full retrieved DFMEA record expanded here]**



This allows a reviewer to confirm the failure mode, effect, cause, controls, recommendation, requirement ID, failure mode ID, and unique test marker without opening the original file immediately.

The same evidence fields are carried into generated DFMEA and DVP&R rows. If no sufficiently relevant source exists, the application labels the row as a rules-based fallback. It does not invent retrieval confidence.

## Connecting DFMEA risks to validation

The application generates stable identifiers for functions, requirements, failure modes, actions, and validation tests.

The function text is specific to the engineering purpose instead of repeating one generic sentence for every row. Requirement text and IDs remain consistent across DFMEA, DVP&R, and traceability outputs.

For each DFMEA row, the application includes:

- item and function;
- risk category;
- potential failure mode;
- local and vehicle-level effects;
- causes and current controls;
- severity, occurrence, and detection;
- RPN as a supporting metric;
- AIAG-VDA-aligned Action Priority;
- recommended action and action tracking;
- source evidence and review status.



**[SCREENSHOT 5: Add the generated DFMEA table showing stable IDs, different Function values, Action Priority, and source columns here]**



The DVP&R rows inherit the linked failure mode, function, and requirement. They include the validation method, objective, stage, sample size, responsible team, acceptance-criteria status, and execution fields.

The traceability view then checks whether every known risk has appropriate validation coverage.



**[SCREENSHOT 6: Add the Traceability tab showing covered, partial, and gap statuses here]**



The gap engine flags conditions such as:

- a DFMEA requirement without linked validation;
- a DVP&R test linked to an unknown failure mode;
- a high-severity recommendation without retrieved evidence;
- a strong retrieved source that no generated row uses;
- an intentional demonstration gap requiring engineer closure.

This is the part of the project I find most valuable. The system does not only generate documents. It checks relationships between them and makes uncertainty visible.

## Evaluating the RAG instead of relying on a demo

A convincing demo query is not enough to establish retrieval quality.

I created a reproducible benchmark containing 30 unique, source-specific engineering questions. Each question defines:

- the expected source document;
- an expected marker inside that source;
- an unrelated forbidden distractor document.

The benchmark includes historical DFMEA records, DVP&R records, lessons learned, joining standards, corrosion standards, a roof-rail CAE report, and an unrelated infotainment launch issue used as a negative example.

I measured:

- Recall@1, Recall@3, and Recall@5;
- mean reciprocal rank;
- exact top-1 citation accuracy;
- top-5 distractor rejection;
- average and P95 retrieval latency.

The current results are:

| Embedding mode | Recall@1 | Recall@3 | Recall@5 | MRR | Exact citation@1 | Distractor rejection@5 |
|---|---:|---:|---:|---:|---:|---:|
| MiniLM semantic | 93.3% | 100% | 100% | 0.967 | 93.3% | 100% |
| Hashed BOW fallback | 96.7% | 100% | 100% | 0.983 | 86.7% | 100% |



**[SCREENSHOT 7: Add a chart or screenshot of the benchmark results from EVALUATION.md here]**



The fallback retriever performs slightly better on exact-document top-1 retrieval because the controlled corpus contains distinctive identifiers and vocabulary. MiniLM performs better on exact citation-marker accuracy, which means it more often returns the specific chunk containing the expected evidence.

This is an important reminder that benchmark results require interpretation. These are small, synthetic, closed-world results. They are not production accuracy claims, and they do not prove generalization to unseen OEM terminology or independently authored documents.

The benchmark is checked into the repository, along with raw per-question results and an evaluation script. CI runs the fallback benchmark on every push and enforces minimum quality thresholds.

## What the application exports

The final workflow produces:

- a DFMEA CSV;
- a DVP&R CSV;
- a Markdown pilot report;
- a formatted multi-sheet Excel review workbook.

The Excel workbook includes the management summary, dashboard, FMEA header, component inputs, knowledge-base summary, retrieved sources, P-Diagram, DFMEA, DVP&R, traceability, gap analysis, lessons learned, pilot metrics, settings, and a readiness checklist.



**[SCREENSHOT 8: Add the Export tab or the opened Excel workbook here]**



The output is still a draft. Requirement targets, acceptance criteria, evidence links, execution results, and approvals must be completed by responsible engineers.

## What I learned while building it

### 1. RAG quality depends on document structure

Chunking a spreadsheet like ordinary prose destroys engineering context. Preserving an entire DFMEA or DVP&R row makes citations and downstream traceability much stronger.

### 2. Retrieval must be observable

Similarity scores alone are not enough. Users need the complete record, source location, metadata, and chunk ID to evaluate whether the match is actually useful.

### 3. Semantic and lexical retrieval should not be confused

A lexical fallback is valuable for offline operation and CI, but users should know when the semantic model is unavailable. Transparency about the active retriever is part of trustworthy AI behavior.

### 4. Structured workflows benefit from deterministic logic

An LLM is not necessary for every step. Domain rules are often more predictable for baseline structure, identifiers, scoring calculations, and coverage checks.

### 5. Evaluation changes the quality of engineering decisions

Creating a benchmark exposed component-conflict problems and citation-level weaknesses that a few successful demo queries would not have revealed.

### 6. Human review should be designed into the data model

Review status, engineer decision, closure evidence, action owner, and approval fields should not be added after generation. They are part of the workflow itself.

## Current limitations

I want this project to demonstrate responsible AI engineering, so its limitations are explicit:

- The public corpus and benchmark are synthetic.
- The benchmark is small and concentrated on BIW engineering.
- MiniLM is a general-purpose model, not an automotive-domain fine-tuned model.
- The vector store is suitable for a prototype, not enterprise-scale retrieval.
- The Streamlit application is currently a single-process architecture.
- There is no authentication, RBAC, tenant isolation, malware scanning, or immutable enterprise audit log.
- The optional LLM mode does not yet have an answer-level faithfulness benchmark.
- The application is AIAG-VDA aligned, but it is not certified or endorsed by AIAG or VDA.
- It cannot approve a design, release a component, close a validation issue, or accept residual risk.

A production pilot would require approved internal data, independent expert relevance labels, hard negative documents, SSO, governed persistence, security review, monitoring, auditability, and stronger answer-level evaluation.

## Why this project matters for my career transition

I am transitioning from automotive engineering into AI engineering, but I do not see those experiences as separate.

Automotive engineering taught me to think in terms of failure modes, evidence, interfaces, validation, traceability, and responsible approval. AI engineering gives me new tools for retrieval, automation, evaluation, and knowledge reuse.

This project connects those two disciplines.

It demonstrates that my goal is not simply to call an LLM API. I want to build AI systems that solve domain-specific problems, expose their evidence, quantify their performance, fail visibly, and remain accountable to human experts.

The next phase is to expand the benchmark with independently authored questions, introduce harder near-neighbor distractors, measure answer faithfulness for optional LLM suggestions, and evaluate whether the workflow reduces engineering review time without reducing quality.

If you work in automotive engineering, applied AI, retrieval systems, or engineering knowledge management, I would value your feedback.

Live application: https://huggingface.co/spaces/vinayanand2/dfmea-assistant

Source code: https://github.com/vinayanand3/dfmea-assistant

## Suggested Medium tags

Artificial Intelligence, RAG, Automotive Engineering, Machine Learning, AI Engineering
