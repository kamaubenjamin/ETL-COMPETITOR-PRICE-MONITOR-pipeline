# Workflow Query Facade v1 Handoff

**Milestone:** v0.10
**State:** Implemented and verified; closure commit and owner tag pending

## Current State

The Document Intelligence API now reads deterministic preview records through a Workflow-owned public query facade. The API facade adapter is preferred; the original API-local provider remains available for compatibility. No live runtime state, persistence, auth, mutation, or external service is connected.

## Important Files

- `src/workflow_runtime/query_facade/__init__.py`: public exports.
- `contracts.py`: filters and ordering contracts.
- `read_models.py`: immutable privacy-safe projections.
- `pagination.py`: bounded page request/result contracts.
- `errors.py`: stable facade-safe errors.
- `ports.py`: narrow read-only structural ports.
- `providers/in_memory.py`: deterministic facade implementation.
- `src/api/document_intelligence/providers/facade_provider.py`: v0.9 API adapter.
- `tests/workflow_runtime/query_facade/`: contract, provider, privacy, and boundary tests.
- `tests/api/document_intelligence/`: API parity and security tests.
- `docs/adr/ADR-015-workflow-query-facade.md`: ownership and dependency decision.

## Verification Commands

```text
python -m pytest tests/workflow_runtime/query_facade -q
python -m pytest tests/api/document_intelligence -q
python -m pytest tests/ui/streamlit -q
python -m pytest tests/review_runtime -q
python scripts/verify_boundaries.py
python -m py_compile src/api/document_intelligence/providers/facade_provider.py
python -m py_compile src/workflow_runtime/query_facade/providers/in_memory.py
python -m pytest -q
git diff --check
```

## Extension Rules

- Add new read fields through explicit immutable models and API mapping tests.
- Add live sources through narrow injected adapters implementing existing or deliberately extended ports.
- Keep composition explicit; do not add service locators, dynamic discovery, or silent preview fallback.
- Preserve deterministic ordering, bounded pagination, safe filters, and privacy allowlists.
- Preserve v0.9 API envelopes and payload meanings unless a separately versioned contract is approved.
- Add import-boundary, privacy, unavailable-source, concurrency, and full-regression tests for every source adapter.

## What Not To Change

- Do not import runtime repositories, services, stores, or models directly into `query_facade` or the API adapter.
- Do not expose raw documents, rows, correction values, artifact payloads, exceptions, stack traces, storage paths, or unrestricted metadata.
- Do not add commands or mutation routes to the read facade.
- Do not connect a database before persistence, retention, consistency, and tenant policy are approved.
- Do not modify legacy `src/api/app.py`, root `dashboard.py`, or competitor-price modules as part of Document Intelligence facade work.

## API And UI Boundary

The Document Intelligence API owns HTTP behavior. Streamlit and future FlowSync Document Intelligence consume the API; they do not import facade implementations or own query semantics. Existing FlowSync Competitor Price remains a separate product.

## Known Risks And Deviations

- Current data is deterministic preview data rather than live operational state.
- Cross-source transactional snapshot consistency is unresolved.
- Limit/offset pagination may not suit high-volume mutable production projections.
- Nine API transport tests skip because the optional TestClient/httpx dependency is unresolved.
- Runtime boundary verification reports two pre-existing BOM-affected files.
- Production identity, tenant policy, persistence, availability objectives, and telemetry are absent.

## Next Recommended Milestone

Plan a live query source adapter and composition-root milestone. Define source ownership, snapshot consistency, unavailable-source behavior, identity, authorization, tenant filtering, persistence strategy, and operational telemetry before connecting production state. Mutation endpoints remain a separate later architecture decision.
