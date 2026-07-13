# ADR-019: Lifecycle Snapshot Advancement v1

## Status

Accepted. Phases 1-4 contracts, pure policy, repository-injected advancement service, optional writer integration, and read-after-advance verification are implemented; release closure remains pending.

## Context

v0.13 appends privacy-safe lifecycle events and writes processing, validation, matching, review, workflow, and audit records. The mutable `DocumentRecord` projection is created at `received` but is not advanced by later lifecycle events. Query Facade, API, and Streamlit therefore cannot show the latest approved document lifecycle status from the document projection.

The solution must retain append-only events as audit truth, preserve optimistic repository semantics, centralize policy across writers, and keep API/UI consumers read-only.

## Decision

Create a dedicated lifecycle package:

```text
src/document_state/lifecycle/
```

It will contain immutable advancement contracts, stable errors/results, an explicit transition catalog, a narrow advancement port, and a repository-injected `LifecycleAdvancementService`.

Document State owns this package because lifecycle projection consistency is a persistence-domain invariant shared by ingestion, processing, review, and workflow writers.

## Rejected Locations

- `src/document_state/writers/lifecycle.py` is rejected because lifecycle policy must not be embedded in or duplicated across writer implementations.
- `src/workflow_runtime/lifecycle/` is rejected because Workflow Runtime does not own ingestion/review state and must not become a persistence coordinator.

## State Decision

v1 preserves the existing `DocumentStatus` values. It does not add transient or overlapping API-visible states.

- Processing is represented by processing snapshots and `current_stage`.
- Structured output maps to `parsed`.
- Reprocess planning remains a reprocess-plan record and does not advance status by itself.
- Processing/review skip remains in its owning record and does not silently become document completion.

Normal document progress follows an explicit directed graph from `received` through ingestion, classification, parsing, extraction, transformation, validation, matching/review, approval, export readiness, and `exported`. Any non-terminal state may explicitly fail. `exported` is terminal. `failed` permits recovery only with an explicit recovery contract linked to a reprocess plan or governed reason and an approved target mapping.

The policy never infers transitions from enum order, timestamps alone, arbitrary stage names, or metadata.

Phase 1 realizes this decision through dependency-light immutable contracts, stable results/errors, state constants, and pure policy functions. It deliberately contains no repository calls, `DocumentRecord` updates, writer integration, or lifecycle service.

## Advancement Service Decision

Use a dedicated service rather than implementing updates independently in writers or repositories.

- Repositories remain persistence mechanisms and do not own business transition policy.
- Writers append lifecycle history and delegate projection advancement.
- The service reads and updates `DocumentRecord` through injected repository ports.
- The service updates status, current stage, event time, and version only.
- The service does not append history, choose a backend, call runtime implementations, or expose public mutation behavior.

Phase 2 implements the service directly against narrow public `DocumentReadRepository` and `DocumentWriteRepository` ports. An explicit `lifecycle_event_persisted` invocation flag distinguishes an ordinary optimistic conflict from a committed-audit/pending-projection conflict without requiring the service to query or mutate lifecycle history.

## Ordering And Consistency Decision

The integrated writer flow is audit-first:

1. Load the current document and validate transition policy.
2. Append the lifecycle event idempotently.
3. Update the document projection using compare-and-swap.

This preserves lifecycle history if projection update fails. Because existing repository ports do not provide a cross-record unit of work, a committed event may temporarily lead its snapshot. The writer returns `projection_pending`; replay of the same event repairs the projection or reports that it is already applied.

No distributed exactly-once or atomic multi-record claim is made.

Phase 3 applies this ordering in the shared lifecycle append helper: policy is prevalidated from the current document, the event is appended idempotently, and the injected service is called with persisted-event context. Projection conflicts return the new bounded writer status `projection_pending`; replay reuses the event identity and can repair the snapshot. Writers without an injected service preserve v0.13 append-only behavior.

Phase 4 verifies this decision across explicit in-memory and SQLite compositions, including reconstruction of the durable composition before readback. Advanced projections flow through the existing Query Facade adapter and API provider without direct persistence imports, endpoint changes, payload changes, or UI mutation behavior.

## Version And Replay Decision

- Every attempted advancement uses the caller-observed `expected_version`.
- Success writes exactly `expected_version + 1`.
- Stale versions fail safely; no last-write-wins or hidden retries are allowed.
- Same-status replay is a projection no-op and does not increment version.
- A later valid state is never regressed by replay of an older event.
- Conflicting content under an existing event/idempotency identity remains a conflict.

## Failure And Recovery Decision

- Invalid transitions reject before append in the ordinary path.
- Missing documents return `not_found`.
- Repository outages return `source_unavailable` without driver detail.
- Raw exception text and stack traces are never returned or persisted.
- Reprocess planning does not itself change document status.
- Recovery from `failed` requires a safe existing reprocess-plan reference whose document and target stage match the requested recovery transition.
- Skipped processing/review outcomes do not advance the document unless a future separately approved document-disposition contract is added.

## Read Projection Decision

No Query Facade, API, or Streamlit contract change is required. Existing adapters already project `DocumentRecord.status` and `current_stage`. Once the snapshot advances, document list/detail reads reflect it automatically.

Processing status remains sourced from processing snapshots. Review queue data remains sourced from review records. Existing API paths, filters, envelopes, request IDs, security headers, GET-only behavior, and Streamlit modes remain unchanged.

## Privacy Decision

Lifecycle contracts and results accept only bounded identities, statuses, stages, timestamps, versions, reason codes, and optional safe reprocess-plan identity. They exclude raw documents, rows, correction values, artifact payloads, storage paths, credentials, raw exceptions, and stack traces. Event metadata is not copied wholesale into the document projection.

## Consequences

### Positive

- Document status becomes accurate for all read consumers without API/UI mutation.
- One policy governs all writers and both repository backends.
- Append-only audit history remains authoritative.
- Replay and optimistic conflicts become explicit and testable.
- Query Facade and API contracts remain stable.

### Negative

- Append and snapshot update are not one transaction.
- Writers require an additional injected lifecycle port.
- Recovery validation needs a narrow read of reprocess plans.
- Legacy histories may need later backfill/rebuild tooling.
- Skipped document disposition remains unresolved by design.

## Deferred Decisions

- Cross-record unit of work, transactional outbox, and background reconciliation.
- Bulk projection rebuild and historical backfill tooling.
- Runtime producer adapters and production bootstrap activation.
- Public mutation endpoints, upload UI/API, auth/authz, and tenants.
- New document-disposition statuses such as skipped/cancelled.
- PostgreSQL/Supabase production activation and operational telemetry.
- Raw encrypted blob storage, FlowSync Document Intelligence, OCR, LLM, and external services.

## Compatibility

ADR-019 is additive to ADR-016, ADR-017, and ADR-018. It preserves Document State repository interfaces, existing document statuses, Query Facade models, v0.9 API payload meanings, Streamlit behavior, legacy API/dashboard, and competitor-price separation.
