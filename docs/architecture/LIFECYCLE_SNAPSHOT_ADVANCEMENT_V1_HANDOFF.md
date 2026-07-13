# Lifecycle Snapshot Advancement v1 Handoff

**Milestone:** v0.14
**State:** Implemented and verified; closed pending owner tag

## Current State

Document State has a governed lifecycle policy and a repository-neutral `LifecycleAdvancementService`. Writer services can optionally append lifecycle events and advance the mutable `DocumentRecord` projection. The approved read path now exposes the latest accepted status and current stage through the Workflow Query Facade, Document Intelligence API provider, and Streamlit `api_preview` without changing consumer contracts.

Lifecycle integration is not automatically activated. Application composition and concrete runtime producer adapters remain future work.

## Important Files

- `src/document_state/lifecycle/contracts.py`: transition, policy-decision, and recovery contracts.
- `src/document_state/lifecycle/states.py`: lifecycle state vocabulary, priorities, terminal states, and explicit transition catalog.
- `src/document_state/lifecycle/policy.py`: pure deterministic transition evaluation.
- `src/document_state/lifecycle/results.py`: bounded advancement outcomes.
- `src/document_state/lifecycle/errors.py`: privacy-safe lifecycle error codes.
- `src/document_state/lifecycle/service.py`: repository-injected projection advancement.
- `src/document_state/writers/_service_support.py`: shared prevalidate-append-advance mechanics.
- `src/document_state/writers/ingestion_writer.py`: received and classified lifecycle integration.
- `src/document_state/writers/processing_writer.py`: parsed, validated, and matched integration.
- `src/document_state/writers/review_writer.py`: review-required and approved integration.
- `src/document_state/writers/workflow_writer.py`: exported and failed integration.
- `tests/document_state/lifecycle/`: policy, service, boundary, backend, replay, and read-path coverage.
- `tests/document_state/writers/test_lifecycle_advancement_integration.py`: writer integration and repair behavior.
- `tests/api/document_intelligence/test_lifecycle_read_after_advance_provider.py`: API-provider compatibility.
- `docs/adr/ADR-019-lifecycle-snapshot-advancement.md`: governing decision.

## How To Verify

```text
python -m pytest tests/document_state/lifecycle -q
python -m pytest tests/document_state/writers -q
python -m pytest tests/document_state -q
python -m pytest tests/api/document_intelligence -q
python -m pytest tests/workflow_runtime/query_facade tests/ui/streamlit tests/review_runtime -q
python scripts/verify_boundaries.py
python -m py_compile src/document_state/lifecycle/service.py
python -m py_compile src/document_state/writers/ingestion_writer.py
python -m py_compile src/document_state/writers/processing_writer.py
python -m py_compile src/document_state/writers/review_writer.py
python -m py_compile src/document_state/writers/workflow_writer.py
python -m pytest -q
git diff --check
```

The full suite may regenerate `price_history.csv`, `src/canonical_products.json`, `src/schedules.json`, and `src/storage/workflow_history.json`. Restore only those known files when they were clean before verification.

## Extension Rules

- Keep lifecycle policy explicit; add graph edges through the governed catalog with policy tests.
- Inject `LifecycleAdvancementService` and repository ports from an owner-approved composition root.
- Keep concrete producer adapters in the producer runtime that owns the source result.
- Emit explicit lifecycle commands; do not infer document state from arbitrary stage names or metadata.
- Append lifecycle events before projection advancement and preserve stable event identity across retries.
- Treat `projection_pending` as committed audit history requiring projection repair, not as a missing event.
- Verify changes against both in-memory and SQLite backends and through the approved read path.
- Preserve current API and Query Facade status vocabularies unless a separate contract milestone approves expansion.

## What Not To Change

- Do not mutate or replace append-only lifecycle history.
- Do not let writers construct the lifecycle service or select repository backends.
- Do not hide optimistic conflicts with last-write-wins or unbounded retries.
- Do not make reprocess-plan creation automatically change document status.
- Do not merge review-case state into document lifecycle state.
- Do not give API or Streamlit direct lifecycle, writer, or repository access.
- Do not store raw documents, rows, correction values, artifacts, paths, credentials, stack traces, or raw exceptions.
- Do not modify legacy `src/api/app.py`, root `dashboard.py`, or competitor-price modules.

## Replay And Recovery Rules

- Same-status replay returns no-op and does not increment version.
- A conflicting event identity with different content remains a conflict.
- A committed event followed by an optimistic projection conflict returns `projection_pending`.
- Replay through a healthy service may repair the projection without duplicating the event.
- `exported` is terminal.
- `failed` recovery requires an explicit valid `RecoveryPolicy`; repository-backed reprocess-plan verification remains deferred.

## UI And API Boundaries

```text
Writer services
  -> LifecycleAdvancementService
  -> DocumentRecord projection update
  -> Document State repositories
  -> DocumentStateQueryFacadeAdapter
  -> Workflow Query Facade
  -> Document Intelligence API
  -> Streamlit api_preview
```

The API remains GET-only. Streamlit remains read-only. Neither layer owns lifecycle policy or repository writes.

## Known Risks And Deviations

- Event append and projection update are separate operations; no cross-record transaction or outbox exists.
- Recovery policy is contract-validated but is not yet verified against repository-backed reprocess plans.
- Production composition does not automatically inject the advancement service.
- Concrete runtime producer adapters and bulk historical projection rebuild are absent.
- SQLite remains local/dev durability; PostgreSQL/Supabase are deferred.
- Nine optional API transport tests remain skipped.
- Boundary verification reports two pre-existing U+FEFF parse warnings.

## Next Recommended Milestone

Plan a narrow runtime producer-adapter and composition-activation milestone. It should wire approved internal producer outputs to existing writer commands and explicitly inject Document State repositories and `LifecycleAdvancementService`. Keep public mutations, upload UI/API, auth/tenant policy, raw blob storage, and production database activation as separate decisions.
