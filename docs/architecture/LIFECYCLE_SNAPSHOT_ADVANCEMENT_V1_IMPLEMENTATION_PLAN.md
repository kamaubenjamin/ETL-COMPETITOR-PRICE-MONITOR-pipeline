# Lifecycle Snapshot Advancement v1 Implementation Plan

**Milestone:** v0.14
**Status:** Phases 1-2 complete; Phases 3-5 not started

## 1. Milestone Overview

v0.14 turns append-only lifecycle events into deterministic updates of the mutable `DocumentRecord` projection. Work is split into five single-session phases. Each phase stops after its own implementation and verification.

The implementation must preserve the existing `DocumentStatus` contract, repository interfaces, v0.9 API paths/payload meanings, Query Facade models, Streamlit UI, and read-only consumer boundaries.

## 2. Phase 1: Lifecycle Transition Contracts And Policy Catalog

### Objectives

- Create immutable advancement request/plan/result contracts and safe errors.
- Define an explicit transition catalog using existing document statuses.
- Define terminal, failure, same-state, skipped, and reprocess recovery behavior.
- Keep policy pure and dependency-light.

### Expected Files

Create:

- `src/document_state/lifecycle/__init__.py`
- `src/document_state/lifecycle/contracts.py`
- `src/document_state/lifecycle/errors.py`
- `src/document_state/lifecycle/policy.py`
- `src/document_state/lifecycle/results.py`
- `src/document_state/lifecycle/states.py`
- `tests/document_state/lifecycle/__init__.py`
- `tests/document_state/lifecycle/test_contracts.py`
- `tests/document_state/lifecycle/test_policy.py`
- `tests/document_state/lifecycle/test_results.py`
- `tests/document_state/lifecycle/test_boundaries.py`

Modify:

- `src/document_state/__init__.py` only for deliberate public exports.
- v0.14 status documentation.

### Tests

- Contracts are frozen and JSON-compatible.
- Every allowed edge is enumerated.
- Backward/unknown transitions reject deterministically.
- `exported` is terminal.
- `failed` recovery requires explicit reprocess context.
- Same-state requests produce no-op plans.
- `processing`, `structured`, `reprocess_planned`, and `skipped` are handled as documented without changing API-visible status values.
- Errors contain codes/status names only.
- Forbidden imports are absent.

### Verification

```text
python -m pytest tests/document_state/lifecycle -q
python -m pytest tests/document_state/writers -q
python scripts/verify_boundaries.py
python -m py_compile src/document_state/lifecycle/contracts.py
python -m py_compile src/document_state/lifecycle/policy.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after contracts, catalog, and tests. Do not implement repository updates or writer integration.

Phase 1 completed with immutable transition/recovery/decision contracts, stable result and error codes, an explicit existing-status transition catalog, deterministic candidate ordering, same-state no-op behavior, terminal-state rejection, governed failed-state recovery, privacy-safe metadata validation, and recursive import/service absence checks. No repository, service, writer, API, or UI implementation was added.

## 3. Phase 2: Lifecycle Advancement Service

### Objectives

- Implement a repository-injected `LifecycleAdvancementService`.
- Load the document, evaluate policy, validate optional reprocess linkage, and update with compare-and-swap.
- Return deterministic advanced/no-op/conflict/not-found/unavailable results.
- Support both active repository backends without concrete imports.

### Expected Files

Create:

- `src/document_state/lifecycle/service.py`
- `tests/document_state/lifecycle/test_service.py`

Modify:

- `src/document_state/lifecycle/__init__.py`.
- `src/document_state/__init__.py` only if needed.
- v0.14 status documentation.

### Tests

- Valid transition updates status/current stage/time/version.
- Update writes exactly `expected_version + 1`.
- Same-state replay does not write or increment version.
- Stale version conflicts safely.
- Missing document and unavailable source map safely.
- Invalid transition leaves the document unchanged.
- Reprocess recovery validates plan/document/target linkage.
- Two same-version updates cannot both win.
- In-memory and SQLite projections are equivalent.
- Service exposes no append or backend-selection behavior.

### Verification

```text
python -m pytest tests/document_state/lifecycle -q
python -m pytest tests/document_state -q
python scripts/verify_boundaries.py
python -m py_compile src/document_state/lifecycle/service.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after service and backend verification. Do not integrate writers.

Phase 2 completed with a narrow repository-injected advancement service, optional bounded source-stage projection, policy evaluation, same-state replay no-op, compare-and-swap updates, in-memory/SQLite verification, two-writer conflict protection, safe missing/conflict/unavailable/internal mappings, explicit projection-pending behavior for already-persisted lifecycle events, and append-only event immutability checks. No separate port module was needed before writer integration because the service itself remains the internal Phase 2 boundary.

## 4. Phase 3: Writer Integration With Advancement Service

### Objectives

- Add narrow lifecycle advancement injection to writers that append lifecycle events.
- Preserve event append idempotency and writer compatibility.
- Use prevalidation, append, then compare-and-swap advancement.
- Return bounded projection-pending results for partial completion.

### Expected Files

Modify only as required:

- `src/document_state/writers/ports.py`
- `src/document_state/writers/results.py`
- `src/document_state/writers/ingestion_writer.py`
- `src/document_state/writers/processing_writer.py`
- `src/document_state/writers/review_writer.py`
- `src/document_state/writers/workflow_writer.py`
- `src/document_state/writers/_service_support.py`
- relevant existing writer tests.
- v0.14 status documentation.

Create:

- `tests/document_state/lifecycle/test_writer_integration.py`
- `tests/document_state/lifecycle/test_partial_retry.py`

### Tests

- Received/classified and explicit processing/review/workflow lifecycle writes advance snapshots.
- Writers never infer lifecycle from processing/workflow/review metadata.
- Append failure prevents advancement.
- Snapshot conflict after append reports projection pending.
- Identical retry does not duplicate history and repairs projection.
- Invalid transition is rejected before append in the ordinary path.
- Existing v0.13 writer behavior remains compatible where advancement is not injected.
- Writer imports remain backend/API/UI/runtime neutral.

### Verification

```text
python -m pytest tests/document_state/lifecycle tests/document_state/writers -q
python -m pytest tests/document_state -q
python scripts/verify_boundaries.py
python -m py_compile src/document_state/writers/ingestion_writer.py
python -m py_compile src/document_state/writers/processing_writer.py
python -m py_compile src/document_state/writers/review_writer.py
python -m py_compile src/document_state/writers/workflow_writer.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after writer integration and retry verification. Do not change API or UI.

## 5. Phase 4: Read-After-Advance Integration Verification

### Objectives

- Verify complete event-to-snapshot-to-read projection behavior.
- Prove in-memory/SQLite parity and reopen durability.
- Verify Query Facade, API-provider, and Streamlit API-provider compatibility.
- Add no new product behavior unless a verified defect requires the smallest fix.

### Expected Files

Create:

- `tests/document_state/lifecycle/test_read_after_advance_integration.py`
- `tests/api/document_intelligence/test_lifecycle_advancement_provider.py`

Modify only if a verified issue is found:

- lifecycle service/policy/writer modules.
- existing integration fixtures/tests.
- v0.14 status documentation.

### Tests

- Full approved lifecycle updates document list/detail status and current stage.
- Processing status remains sourced from processing snapshots.
- Review queue remains sourced from review records.
- Reprocess planning does not falsely advance document status.
- Recovery linkage and later progress are visible deterministically.
- Backend projections remain equal after SQLite reconstruction.
- API paths, envelopes, payload keys, filters, request IDs, headers, and GET-only methods remain unchanged.
- Streamlit API-provider shapes remain compatible.
- Privacy assertions cover history, snapshot, facade, and API projection.

### Verification

```text
python -m pytest tests/document_state/lifecycle tests/document_state/writers -q
python -m pytest tests/document_state -q
python -m pytest tests/workflow_runtime/query_facade -q
python -m pytest tests/api/document_intelligence tests/ui/streamlit tests/review_runtime -q
python scripts/verify_boundaries.py
python -m pytest -q
git diff --check
git status --short --branch
```

### Stop Condition

Stop after read-after-advance, privacy, compatibility, and boundary verification.

## 6. Phase 5: Documentation, Release Closure, And Handoff

### Objectives

- Run focused and full regressions.
- Document delivered policy, service, writer integration, limitations, and recovery semantics.
- Add release summary, future-agent handoff, and release notes.
- Prepare but do not create the owner tag.

### Expected Files

Create:

- `docs/architecture/LIFECYCLE_SNAPSHOT_ADVANCEMENT_V1_SUMMARY.md`
- `docs/architecture/LIFECYCLE_SNAPSHOT_ADVANCEMENT_V1_HANDOFF.md`
- `docs/releases/v0.14-lifecycle-snapshot-advancement.md`

Modify:

- both v0.14 plans.
- `docs/adr/ADR-019-lifecycle-snapshot-advancement.md`.
- `docs/ROADMAP.md`.
- `TECHNICAL_DEBT.md`.
- `CHANGELOG.md`.

### Verification

```text
python -m pytest tests/document_state/lifecycle tests/document_state/writers -q
python -m pytest tests/document_state -q
python -m pytest tests/workflow_runtime/query_facade -q
python -m pytest tests/api/document_intelligence tests/ui/streamlit tests/review_runtime -q
python scripts/verify_boundaries.py
python -m pytest -q
git diff --check
git status --short --branch
```

### Stop Condition

Stop after documentation and verification. Do not commit, push, or tag unless explicitly instructed.

## 7. Boundary Requirements

- `document_state.lifecycle` imports only standard library and public/package-local Document State contracts and repository ports.
- Lifecycle policy has no repository, writer, API, UI, Query Facade, runtime, persistence-engine, storage, telemetry, or external imports.
- Service receives repository ports and never imports SQLite/in-memory implementations or composition.
- Writers receive a lifecycle port and never construct the service.
- API, Streamlit, and Query Facade remain read-only and import no lifecycle service or writers.
- Legacy API/dashboard and competitor-price modules remain untouched.

## 8. Backward Compatibility Requirements

- Preserve existing `DocumentStatus` values and v0.9 filter allowlists.
- Preserve Document State repository Protocol method signatures.
- Preserve v0.13 writer commands and non-integrated construction where practical.
- Preserve Query Facade read models and API payload meanings.
- Preserve Streamlit `local_preview`/`api_preview` behavior.
- No automatic backend or lifecycle service activation.

## 9. Risks And Mitigations

- **History/snapshot partial state:** audit-first append plus explicit projection-pending result and replay repair.
- **Lost updates:** strict compare-and-swap and no hidden version retries.
- **Lifecycle regression:** explicit graph, not numeric rank or stage-name inference.
- **Recovery abuse:** require a linked same-document reprocess plan and mapped target.
- **Duplicate version churn:** same-state replay is a no-op.
- **Cross-writer drift:** one injected lifecycle port and one policy catalog.
- **Contract expansion:** keep transient processing/reprocess/skip state outside `DocumentStatus` in v1.

## 10. Definition Of Done

- Pure contracts and policy exhaustively cover progression, failure, terminal, recovery, and replay behavior.
- Dedicated service updates document snapshots through existing optimistic ports.
- Applicable writers use the shared service without backend or runtime coupling.
- In-memory and SQLite behavior is equivalent.
- Query Facade/API/Streamlit show the latest accepted document status without endpoint/UI changes.
- Privacy, boundaries, focused tests, and full regression pass.
- Release summary, handoff, notes, roadmap, debt, changelog, and ADR are complete.

## 11. Commit And Tag Strategy

Recommended owner-reviewed commits:

1. `feat: add lifecycle transition contracts and policy`
2. `feat: add lifecycle snapshot advancement service`
3. `feat: integrate writers with lifecycle advancement`
4. `test: verify lifecycle read-after-advance behavior`
5. `chore: close v0.14 lifecycle snapshot advancement`

Recommended tag after Phase 5 owner verification:

`v0.14-lifecycle-snapshot-advancement`
