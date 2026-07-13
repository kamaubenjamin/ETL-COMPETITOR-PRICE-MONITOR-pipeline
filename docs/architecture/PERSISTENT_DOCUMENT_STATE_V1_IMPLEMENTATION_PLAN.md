# Persistent Document State v1 Implementation Plan

**Milestone:** v0.11
**Status:** Phases 1-3 complete; Phases 4-5 pending

## 1. Milestone Overview

v0.11 implements persistence-neutral Document State contracts, deterministic in-memory repositories, and a read-only adapter to the existing Workflow Query Facade. Each phase is one narrow Codex session and stops before the next phase. No database, migration, API/UI change, live runtime writer, auth, OCR, LLM, or external service is included.

## 2. Phase 1: Persistent State Contracts And Repository Interfaces

**Completion note:** Added dependency-free `src/document_state/` contracts with ten frozen JSON-compatible record types, safe enums and filters, deterministic ordering declarations, bounded pagination, six stable privacy-safe error codes, strict scalar metadata allowlisting, and separate runtime-checkable read/write repository protocols. Mutable write ports expose `expected_version`; append-only ports expose `idempotency_key`. Focused verification: 44 tests passed. Existing Query Facade, API, Streamlit, and Review Runtime regression: 307 passed and 9 conditional transport tests skipped. Boundary verification remained compliant. No repository implementation, adapter, database, migration, API, UI, or runtime integration was added.

### Objectives

- Create `src/document_state/` with immutable safe record contracts.
- Define bounded repository pagination, filters, ordering, and stable errors.
- Define separate read/write `Protocol` ports for each state area.
- Define version and append-idempotency semantics without implementations.
- Record ADR-016 boundary and privacy decisions.

### Expected Files

Create:

- `src/document_state/__init__.py`
- `src/document_state/contracts.py`
- `src/document_state/errors.py`
- `src/document_state/pagination.py`
- `src/document_state/privacy.py`
- `src/document_state/repositories.py`
- `src/document_state/records.py`
- `tests/document_state/__init__.py`
- `tests/document_state/test_contracts.py`
- `tests/document_state/test_pagination.py`
- `tests/document_state/test_privacy.py`
- `tests/document_state/test_repositories.py`
- `tests/document_state/test_records.py`

Modify documentation status files only as required.

### Tests

- Frozen contracts and JSON-compatible serialization.
- Required IDs, timestamps, versions, enums, and bounds.
- Unsafe fields, metadata, values, and error messages rejected.
- Pagination bounds and deterministic ordering declarations.
- Structural read/write protocols remain separate and narrow.
- Core package has no forbidden imports.

### Verification

```text
python -m pytest tests/document_state -q
python scripts/verify_boundaries.py
python -m py_compile src/document_state/records.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after contracts, interfaces, tests, ADR alignment, and verification. Do not implement repositories.

## 3. Phase 2: Deterministic In-Memory Repository Implementation

**Completion note:** Added `InMemoryDocumentStateRepositories` with structurally conformant read-only and write-only views over shared operation-locked state. All ten record groups support their defined get/list/create/update/append operations, deterministic filtering and ordering, bounded pagination, safe missing/conflict/invalid/unavailable errors, defensive contract reconstruction, optimistic version checks, and stable-key append idempotency. Focused verification: 70 tests passed. Existing Query Facade, API, Streamlit, and Review Runtime regression: 307 passed and 9 conditional transport tests skipped. Boundary verification remained compliant. No database, file, network, adapter, API/UI integration, or upload behavior was added.

### Objectives

- Implement explicit in-memory repositories for all v1 record types.
- Support bounded reads, filters, stable ordering, and defensive immutable results.
- Enforce expected-version updates and stable-ID append idempotency.
- Keep operation-level locking deterministic and repository-local.
- Add explicit safe source-unavailable simulation for tests only.

### Expected Files

Create:

- `src/document_state/repositories_in_memory.py`
- `tests/document_state/test_in_memory_repositories.py`

Modify:

- `src/document_state/__init__.py`
- documentation status files

### Tests

- Create/get/list and append behavior across all repository areas.
- Duplicate identical append is idempotent; conflicting duplicate fails safely.
- Versioned update succeeds only for the expected version.
- Pagination/filter/order parity and deterministic repeated reads.
- Empty, missing, invalid, duplicate, conflict, and unavailable behavior.
- Concurrent operation safety and no mutation leakage.
- No persistence, database, external service, or mutation API imports.

### Verification

```text
python -m pytest tests/document_state -q
python scripts/verify_boundaries.py
python -m py_compile src/document_state/repositories_in_memory.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after deterministic in-memory repository implementation. Do not add Query Facade integration or database code.

## 4. Phase 3: Workflow Query Facade Repository Adapter

**Completion note:** Added the read-only `DocumentStateQueryFacadeAdapter` over injected `DocumentStateReadRepositories`. It explicitly projects documents, processing, validation, matching, reviews, corrections, reprocess plans, workflow runs, and audit events into public v0.10 read models; preserves facade ordering, filters, bounded pagination, and snapshot timestamps; translates safe repository errors; and exposes no write surface. Focused Document State verification: 77 tests passed. API/UI composition and database/live source integration remain deferred.

### Objectives

- Add a read-only adapter from Document State read ports to public Workflow Query Facade contracts.
- Map every repository record explicitly into existing v0.10 immutable read models.
- Translate filters, pagination, ordering, and safe errors.
- Prove API provider payload parity without changing API routes or composition.
- Keep Query Facade, API, and UI free of Document State imports.

### Expected Files

Create:

- `src/document_state/adapters/__init__.py`
- `src/document_state/adapters/query_facade_adapter.py`
- `tests/document_state/test_query_facade_adapter.py`

Modify only if public exports require it:

- `src/document_state/__init__.py`
- documentation status files

Do not modify API routes, endpoint contracts, or Streamlit behavior.

### Tests

- Adapter satisfies `WorkflowQueryFacadePort` structurally.
- All document, processing, validation, matching, review, correction, reprocess, workflow, and audit projections map correctly.
- Bounded pagination, filters, stable ordering, unknown IDs, and unavailable source behavior.
- No write methods escape through the adapter.
- Existing v0.10 facade and v0.9 API payload-shape parity.
- Adapter imports only public Document State and Query Facade modules.

### Verification

```text
python -m pytest tests/document_state tests/workflow_runtime/query_facade -q
python -m pytest tests/api/document_intelligence tests/ui/streamlit -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after adapter and parity verification. Do not wire production composition, live writers, database, API, or UI.

## 5. Phase 4: Boundary, Privacy, And Repository Verification

### Objectives

- Recursively verify core, repository, and adapter import rules.
- Verify privacy rejection and absence of raw payloads in every repository/read projection.
- Expand concurrency, idempotency, version conflict, deterministic ordering, and pagination coverage.
- Re-run Query Facade, API security, request-ID, GET-only, Streamlit, and Review Runtime regressions.
- Add no boundary exemptions unless separately approved and documented.

### Expected Files

Create or modify only as evidence requires:

- `tests/document_state/test_boundary_rules.py`
- `tests/document_state/test_privacy_security.py`
- `tests/document_state/test_repository_contract_conformance.py`
- `tests/api/document_intelligence/test_document_state_boundary_integration.py`
- `tests/boundaries/` or `scripts/verify_boundaries.py` only if the new package is not covered

### Tests

- Forbidden imports and reverse dependencies absent.
- API/UI/Query Facade do not import Document State.
- Core Document State does not import Workflow Query Facade; only the explicit adapter may.
- No raw document, row, correction value, artifact payload, stack trace, storage detail, or unsafe metadata persists or projects.
- Expected-version and idempotency behavior under concurrency.
- Existing API paths, payload meanings, envelopes, methods, request IDs, and security headers unchanged.

### Verification

```text
python -m pytest tests/document_state tests/workflow_runtime/query_facade tests/api/document_intelligence -q
python -m pytest tests/ui/streamlit tests/review_runtime tests/boundaries -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after hardening and verification. Do not implement database, live writer, production composition, auth, or endpoints.

## 6. Phase 5: Documentation, Release Closure, And Handoff

### Objectives

- Run focused and full regression suites.
- Add milestone summary, future-agent handoff, and release notes.
- Update plan, ADR, roadmap, technical debt, and changelog accurately.
- Prepare but do not create the final tag.

### Expected Files

Create:

- `docs/architecture/PERSISTENT_DOCUMENT_STATE_V1_SUMMARY.md`
- `docs/architecture/PERSISTENT_DOCUMENT_STATE_V1_HANDOFF.md`
- `docs/releases/v0.11-persistent-document-state.md`

Modify:

- both v0.11 plans
- `docs/adr/ADR-016-persistent-document-state.md`
- `docs/ROADMAP.md`
- `TECHNICAL_DEBT.md`
- `CHANGELOG.md`

### Verification

```text
python -m pytest tests/document_state -q
python -m pytest tests/workflow_runtime/query_facade tests/api/document_intelligence -q
python -m pytest tests/ui/streamlit tests/review_runtime -q
python scripts/verify_boundaries.py
python -m pytest -q
git diff --check
git status --short --branch
```

### Stop Condition

Stop after documentation and verification. Do not commit, push, or tag unless explicitly instructed.

## 7. Boundary Requirements

- Core `document_state` imports standard library and own modules only.
- Concrete repositories import public Document State contracts only.
- The Workflow adapter imports only public Document State and public Query Facade modules.
- Query Facade, API, UI, Streamlit, FlowSync, and competitor-price modules do not import Document State.
- Future writers depend on public write ports, not implementations.
- No database, ORM, storage, telemetry, external-service, OCR, or LLM dependency in v0.11.

## 8. Backward Compatibility Requirements

- Preserve every v0.9 API path, GET method, payload meaning, envelope, request ID, pagination, and security header.
- Preserve v0.10 read model fields, ordering, filter semantics, and safe errors.
- Keep `InMemoryWorkflowQueryFacade` available for existing deterministic tests.
- Preserve Streamlit `local_preview` and `api_preview` behavior.
- Leave legacy `src/api/app.py`, root `dashboard.py`, and competitor-price modules untouched.

## 9. Risks And Mitigations

- **Model duplication:** require explicit adapter and parity tests.
- **False database guarantees:** document only repository-operation atomicity in v0.11.
- **Sensitive persistence:** enforce record allowlists and negative privacy tests before writes.
- **Generic repository growth:** use explicit domain ports, not generic CRUD or arbitrary metadata.
- **Lost update:** require expected versions for mutable snapshots.
- **Duplicate events:** use stable IDs with idempotent identical append and conflict on mismatch.
- **Boundary drift:** recursively scan imports and reject new exemptions by default.

## 10. Definition Of Done

- All five phases complete independently with their stop conditions honored.
- Contracts, in-memory repositories, and facade adapter pass focused tests.
- Privacy, concurrency, idempotency, pagination, and import boundaries are verified.
- Existing Query Facade, API, Streamlit, Review Runtime, boundary, and full regression suites pass.
- No database, migration, API/UI change, live writer, auth, mutation endpoint, or external dependency is added.
- Closure documentation accurately distinguishes deterministic repositories from durable production persistence.

## 11. Commit And Tag Strategy

Recommended commits after owner review of each phase:

1. `feat: add persistent document state contracts`
2. `feat: add deterministic document state repositories`
3. `feat: add document state query facade adapter`
4. `test: harden document state boundaries`
5. `chore: close v0.11 persistent document state`

Recommended tag after Phase 5 owner verification:

`v0.11-persistent-document-state`
