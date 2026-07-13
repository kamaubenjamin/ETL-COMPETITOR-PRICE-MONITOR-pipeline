# Workflow Query Facade v1 Implementation Plan

**Milestone:** v0.10
**Status:** All phases complete; closure commit and owner tag pending

## 1. Milestone Overview

v0.10 adds a Workflow-owned, read-only query boundary for Document Intelligence. Each phase is limited to one Codex session, retains deterministic behavior, and stops before the next phase. The milestone does not connect live runtime stores; it establishes contracts, a deterministic provider, and API integration architecture that future live adapters can safely implement.

## 2. Phase 1: Query Facade Contracts And Read Models

**Completion note:** Implemented frozen standard-library contracts for filters, ordering, bounded pagination, ten privacy-safe read models, four stable facade error codes, seven narrow source protocols, and the aggregate read-only facade protocol. The package has zero runtime/API/UI/storage/telemetry dependencies. Focused verification: 34 tests passed. No provider, service, API adapter, live source, persistence, or mutation behavior was added.

### Objectives

- Create `src/workflow_runtime/query_facade/` and ADR-015-approved public exports.
- Define strict JSON-compatible models for documents, processing, validation, matching, reviews, corrections, reprocess plans, workflow runs, and audit.
- Define page requests/results, fixed filters, sort rules, safe metadata, and facade errors.
- Define narrow source protocols without importing runtime implementations.

### Expected Files

Create:

- `src/workflow_runtime/query_facade/__init__.py`
- `src/workflow_runtime/query_facade/contracts.py`
- `src/workflow_runtime/query_facade/pagination.py`
- `src/workflow_runtime/query_facade/errors.py`
- `src/workflow_runtime/query_facade/ports.py`
- `src/workflow_runtime/query_facade/read_models.py`
- `tests/workflow_runtime/query_facade/__init__.py`
- `tests/workflow_runtime/query_facade/test_contracts.py`
- `tests/workflow_runtime/query_facade/test_pagination.py`
- `tests/workflow_runtime/query_facade/test_read_models.py`
- `tests/workflow_runtime/query_facade/test_ports.py`

### Tests

- Required fields, enum/code allowlists, bounds, timestamps, finite confidence, and strict keys.
- JSON round trips, immutability, defensive metadata, and rejection of raw/controlled values.
- Pagination/filter bounds and stable error codes/messages.
- Static proof that contracts and ports import no runtime internals.

### Verification

```text
python -m pytest tests/workflow_runtime/query_facade -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after contracts, filters, ports, and tests. Do not implement providers, API integration, or live sources.

## 3. Phase 2: Deterministic In-Memory Facade Provider

**Completion note:** Implemented `InMemoryWorkflowQueryFacade` with deterministic immutable fixtures, all Phase 1 port methods, requested processing/correction read aliases, safe filters, bounded pagination, stable ordering, safe not-found/invalid-query/source-unavailable errors, and no mutation or persistence surface. The provider is structurally compatible with `WorkflowQueryFacadePort`; 60 query-facade tests pass. No API, UI, database, external service, or live runtime integration was added.

### Objectives

- Implement the explicit query service and deterministic in-memory source/provider.
- Apply filters before totals/pagination and enforce documented total ordering.
- Return defensive records and stable not-found/unavailable errors.
- Keep fixture content privacy-safe and independent from API/UI fixtures.

### Expected Files

Create or modify:

- `src/workflow_runtime/query_facade/providers/__init__.py`
- `src/workflow_runtime/query_facade/providers/in_memory.py`
- `src/workflow_runtime/query_facade/__init__.py`
- `tests/workflow_runtime/query_facade/test_in_memory_provider.py`

### Tests

- Success and empty behavior for every query method.
- Stable ordering, filters, page boundaries, totals, and repeated-read determinism.
- Input/output immutability and nested defensive copies.
- Missing IDs, invalid query plans, source-unavailable mapping, and no partial silent fallback.
- No raw document, row, correction value, comments, arbitrary metadata, or stack traces.

### Verification

```text
python -m pytest tests/workflow_runtime/query_facade -q
python -m pytest tests/test_workflow_runtime.py -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after deterministic facade behavior. Do not modify API routes or connect live runtime sources.

## 4. Phase 3: API Facade Provider Adapter

**Completion note:** Added `FacadeDocumentIntelligenceProvider`, which translates only public Workflow Query Facade read models into the unchanged v0.9 API provider shapes. The facade-backed deterministic provider is now preferred through the existing package export; the API-local provider remains explicitly available for compatibility. Routes, endpoints, envelopes, pagination metadata, payload meanings, and GET-only behavior are unchanged. Focused API verification: 31 passed and 9 conditional transport tests skipped. No live source, persistence, auth, mutation, or UI behavior was added.

### Objectives

- Add an API-side provider that calls only the public Workflow Query Facade.
- Preserve all v0.9 endpoint paths, payload meanings, filters, envelopes, pagination, request IDs, privacy, and security behavior.
- Keep deterministic API-local provider mode available for isolated tests.
- Make provider selection explicit and prohibit silent fallback.

### Expected Files

Create or modify:

- `src/api/document_intelligence/providers/facade_provider.py`
- `src/api/document_intelligence/providers/__init__.py`
- `src/api/document_intelligence/app.py` only for explicit provider injection if required
- routers only if dependency injection requires a mechanical provider lookup; no route or payload changes
- `tests/api/document_intelligence/test_facade_provider.py`
- `tests/api/document_intelligence/test_facade_parity.py`
- `tests/api/document_intelligence/test_app.py`
- `tests/ui/streamlit/test_api_provider.py` only for regression/parity coverage

### Tests

- Facade-to-API projection parity for every endpoint area.
- Envelope and pagination metadata remain byte-shape compatible.
- Filters, not-found, unavailable, empty, and deterministic ordering behavior.
- No mutation methods or new OpenAPI paths.
- No silent fallback from configured facade mode.
- Streamlit `local_preview` and `api_preview` regressions.

### Verification

```text
python -m pytest tests/workflow_runtime/query_facade tests/api/document_intelligence -q
python -m pytest tests/ui/streamlit -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after deterministic facade-backed API integration. Do not add live sources, database, auth, UI changes, or endpoints.

## 5. Phase 4: Boundary And Security Verification

**Completion note:** Added recursive forbidden-import verification for the Workflow Query Facade package and strict adapter import checks. Added facade/API parity coverage for structural port conformance, all public projections, v0.9 paths and GET-only methods, standard envelopes, pagination, privacy-sensitive keys, request IDs, and security headers. Hardened adapter error translation so `invalid_query`, `not_found`, `source_unavailable`, and `internal_error` retain bounded semantics as safe API `400`, `404`, `503`, and `500` outcomes. Focused verification: 62 Query Facade tests and 41 API tests passed; 9 conditional transport tests skipped. No endpoint, payload meaning, live source, mutation, auth, database, or UI behavior was added.

### Objectives

- Enforce facade import rules with no new exemptions.
- Verify strict public exports and dependency direction.
- Expand privacy, pagination, unavailable-source, concurrency-read, and contract parity coverage.
- Re-run API security/request-ID/method/OpenAPI regressions.

### Expected Files

Create or modify only as evidence requires:

- `tests/workflow_runtime/query_facade/test_boundary_security.py`
- `tests/workflow_runtime/query_facade/test_contract_parity.py`
- `tests/api/document_intelligence/test_security_hardening.py`
- `tests/api/document_intelligence/test_method_restrictions.py`
- `tests/boundaries/` or `scripts/verify_boundaries.py` only if the new package is not covered; explain any focused rule change

### Tests

- Forbidden imports in facade and API adapter.
- No reverse API/UI dependency from facade.
- Bounded metadata/errors and sensitive-key scans.
- Deterministic concurrent reads without source/input mutation.
- GET-only methods, unchanged OpenAPI paths, headers, request IDs, and safe errors.
- No new boundary exemption.

### Verification

```text
python -m pytest tests/workflow_runtime/query_facade tests/api/document_intelligence tests/boundaries -q
python -m pytest tests/ui/streamlit tests/review_runtime -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after verification hardening. Do not implement live adapters, persistence, commands, auth, or deployment configuration.

## 6. Phase 5: Documentation, Release Closure, And Handoff

**Completion note:** Completed the milestone summary, future-agent handoff, release notes, roadmap, technical debt, changelog, plan, and ADR closure updates. Focused verification passed with 62 Query Facade tests, 41 API tests plus 9 conditional skips, 29 Streamlit tests, and 175 Review Runtime tests. Full regression passed with 984 tests, 9 skips, and 711 warnings; boundary verification remained compliant with two pre-existing BOM scan warnings. Four known generated legacy artifacts were restored. No runtime feature, endpoint, payload, dependency, or integration behavior changed.

### Objectives

- Run focused and full regression suites.
- Add summary, handoff, and release notes.
- Update plan, ADR, roadmap, debt, and changelog accurately.
- Prepare but do not create the final tag.

### Expected Files

Create:

- `docs/architecture/WORKFLOW_QUERY_FACADE_V1_SUMMARY.md`
- `docs/architecture/WORKFLOW_QUERY_FACADE_V1_HANDOFF.md`
- `docs/releases/v0.10-workflow-query-facade.md`

Modify:

- `docs/architecture/WORKFLOW_QUERY_FACADE_V1_PLAN.md`
- `docs/architecture/WORKFLOW_QUERY_FACADE_V1_IMPLEMENTATION_PLAN.md`
- `docs/adr/ADR-015-workflow-query-facade.md`
- `docs/ROADMAP.md`
- `TECHNICAL_DEBT.md`
- `CHANGELOG.md`

### Verification

```text
python -m pytest tests/workflow_runtime/query_facade tests/api/document_intelligence -q
python -m pytest tests/ui/streamlit tests/review_runtime tests/boundaries -q
python scripts/verify_boundaries.py
python -m pytest -q
git diff --check
git status --short --branch
```

### Stop Condition

Stop after closure documentation and verification. Do not commit, push, or tag unless separately instructed.

## 7. Cross-Phase Boundary Requirements

- Facade package imports only its own modules, Workflow public contracts where truly required, and standard library.
- No facade module imports API, UI, runtime internals, persistence, telemetry, FlowSync, or competitor-price code.
- API imports only facade public exports, never facade implementation modules or other runtimes.
- Future live adapters are injected through narrow ports and require a separately approved composition decision.
- No new R05 or other boundary exemption.

## 8. Backward Compatibility Requirements

- No v0.9 endpoint path, method, filter, envelope field, payload meaning, pagination limit, error code, request-ID behavior, header, or CORS policy changes.
- Streamlit `local_preview` remains the default; `api_preview` remains explicit.
- API deterministic local provider remains available through migration and tests.
- Breaking query-model changes require contract versioning and ADR review.

## 9. Risks And Mitigations

| Risk | Mitigation |
|---|---|
| Facade accumulates direct runtime imports | Narrow ports, import tests, public exports, no dynamic discovery. |
| Duplicate API/facade models drift | Explicit adapter and parity tests. |
| Snapshot consistency is overstated | Include snapshot metadata and document source limitations. |
| Provider switch hides unavailable live data | Explicit configuration and no silent fallback. |
| Pagination order changes | Per-model stable order and ID tie-breakers. |
| Future tenant leakage | Block production live integration until tenant/auth policy exists. |

## 10. Definition Of Done

- Phases 1-5 are implemented and independently verified.
- All planned read models and explicit queries exist behind the Workflow public facade.
- Deterministic provider and API adapter preserve v0.9 semantics.
- No live source, database, mutation, auth, UI, OCR, LLM, external service, or competitor coupling is introduced.
- Boundary verification passes without new exemptions.
- Full regression and release documentation are complete.

## 11. Commit And Tag Strategy

Recommended one commit per phase:

1. `feat: add workflow query facade contracts`
2. `feat: add deterministic workflow query facade`
3. `feat: connect document api to workflow query facade`
4. `test: harden workflow query facade boundaries`
5. `chore: close v0.10 workflow query facade`

Recommended tag after Phase 5 owner verification:

`v0.10-workflow-query-facade`
