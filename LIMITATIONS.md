# Limitations and Production Gaps

This repository is a tested public prototype, not a released engineering decision system.

## Data and evaluation

- Public examples and benchmark records are synthetic.
- The 30-question benchmark is small, closed-world, English-only, and concentrated on BIW front-rail topics.
- Benchmark questions were written from the same source corpus, so the results do not estimate performance on novel OEM terminology or unseen document styles.
- Recall measures exact expected-document retrieval. Citation exactness additionally requires the expected marker in the top-ranked chunk.
- The benchmark does not yet measure answer faithfulness from an enabled LLM.

## Retrieval

- The local NumPy vector store is appropriate for a small corpus, not enterprise-scale indexing.
- The hashed bag-of-words fallback is lexical, not semantic. It exists for offline development and CI.
- MiniLM is a general-purpose embedding model and has not been fine-tuned on automotive engineering language.
- Component reranking is rule-based and covers a limited component vocabulary.

## Application architecture

- The Streamlit application is a single process and `app.py` remains larger than ideal.
- There is no multi-user isolation, background job queue, database migration layer, or API service boundary.
- Local vector data is not durable on every free hosting configuration.

## Security and governance

- No authentication, role-based access control, tenant isolation, or enterprise audit log is implemented.
- Uploaded documents should be synthetic or explicitly approved non-confidential material.
- The prototype has not completed threat modeling, penetration testing, privacy review, or records-retention review.

## Engineering authority

- The application is AIAG-VDA aligned but is not certified or endorsed by AIAG or VDA.
- Generated ratings, requirements, controls, tests, and acceptance criteria are drafts.
- The tool cannot release a design, close a validation issue, or accept residual risk.
- Controlled numerical targets and sources must be supplied by responsible engineers.

## Next production steps

1. Evaluate on a larger, independently authored and access-controlled corpus.
2. Add answer-level faithfulness and citation-entailment evaluation for LLM mode.
3. Replace local persistence with a governed vector database and document store.
4. Add SSO, RBAC, immutable audit events, encryption, secrets management, and retention controls.
5. Split the monolithic application into UI, domain, retrieval, evaluation, and export services.
6. Add tracing, structured logs, latency and cost monitoring, drift checks, and incident runbooks.
