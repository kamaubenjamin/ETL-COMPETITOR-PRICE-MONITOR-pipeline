# Document Intelligence Operator Console v1 Handoff

**Milestone:** v0.8
**State:** Implemented and verified; release commit and tag pending

## Current State

The repository contains a read-only internal Streamlit console backed by deterministic local providers and a contract-valid Review Runtime preview. It is demo-ready and regression-tested, but it is not connected to live platform state and is not a production operations deployment.

## Run Streamlit

From the repository root:

```text
streamlit run src/ui/streamlit/document_intelligence_app.py
```

If `streamlit` is not on `PATH`:

```text
python -m streamlit run src/ui/streamlit/document_intelligence_app.py
```

## Important Files

- `src/ui/streamlit/document_intelligence_app.py`
- `src/ui/streamlit/data_providers.py`
- `src/ui/streamlit/view_models.py`
- `src/ui/streamlit/components.py`
- `tests/ui/streamlit/`
- `docs/architecture/DOCUMENT_INTELLIGENCE_OPERATOR_CONSOLE_V1_PLAN.md`
- `docs/architecture/DOCUMENT_INTELLIGENCE_OPERATOR_CONSOLE_V1_SUMMARY.md`
- `docs/releases/v0.8-document-intelligence-operator-console.md`

## Extension Rules

- Replace providers behind the existing read-only method boundary; do not fetch live data directly from page code.
- Keep view models pure and JSON/DataFrame-friendly.
- Keep components limited to presentation and copy records before formatting.
- Add explicit empty, loading, unavailable, and unauthorized states for future adapters.
- Route future mutation commands through backend-owned services with identity, authorization, idempotency, and optimistic versions.
- Add privacy, boundary, mutation-isolation, and browser tests with every integration.

## What Not To Change

- Do not make Streamlit the source of truth for documents, workflows, review cases, corrections, decisions, or audit.
- Do not expose raw documents, complete source rows, correction payloads, credentials, or unrestricted metadata.
- Do not enable upload until a backend-owned ingestion boundary exists.
- Do not import competitor-price connectors, workflows, storage, or dashboard modules.
- Do not modify or retire root `dashboard.py` without a separate approved milestone.

## UI And Backend Boundaries

Streamlit owns rendering, navigation, filters, and display-only formatting. Providers adapt data into bounded records. Document, Workflow, Matching, Transform, and Review runtimes continue to own contracts, execution, validation, decisions, and state. Future APIs or application services must enforce authorization and privacy before returning UI view data.

## Streamlit And FlowSync

Streamlit is the internal/operator console. Existing FlowSync Competitor Price remains its own product surface. A future FlowSync Document Intelligence product must use separate planning, contracts, and implementation and must not treat this Streamlit code as its backend.

## Competitor Price Separation

Root `dashboard.py` is the legacy Competitor Price Monitor and remains untouched. v0.8 imports no competitor-price modules and shares no UI state or business logic with that dashboard.

## Known Risks And Deviations

- All displayed data is deterministic local preview data, not operational truth.
- Actor IDs and filenames are synthetic and no authentication is performed.
- Display status/priority vocabulary has not completed operator usability validation.
- Browser-matrix, responsive, and formal accessibility verification remain incomplete.
- Static boundary verification skips two pre-existing BOM-affected files.

## Next Recommended Milestone

Plan a read-only Document Intelligence application-service boundary with trusted identity and authorization. Replace one provider surface at a time, beginning with document/workflow summaries, while retaining deterministic fallback fixtures and keeping all mutation disabled.

