# Lifecycle Snapshot Advancement v1 Plan

**Milestone:** v0.14
**Status:** Accepted; Phases 1-3 implemented, Phases 4-5 not started

## 1. Problem Statement

v0.13 writer services append immutable lifecycle events, but `DocumentRecord.status` and `current_stage` remain at their creation values. Query Facade, API, and Streamlit therefore show `received` even when approved lifecycle history records later progress.

v0.14 introduces one governed projection mechanism that validates lifecycle transitions and advances the mutable document snapshot with optimistic concurrency. Append-only lifecycle history remains the audit truth; the document record remains a rebuildable operational projection.

## 2. Current And Target Architecture

Current path:

```text
Producer / internal runtime output
  -> Document State writer services
  -> append-only lifecycle events and other records
  -> Document State repositories
  -> Query Facade -> API -> Streamlit api_preview
```

Target path:

```text
Producer / internal runtime output
  -> Document State writer service
  -> append lifecycle event idempotently
  -> dedicated LifecycleAdvancementService
  -> compare-and-swap DocumentRecord projection
  -> Document State repositories
  -> DocumentStateQueryFacadeAdapter
  -> Workflow Query Facade
  -> Document Intelligence API
  -> Streamlit api_preview
```

The event is authoritative. Snapshot advancement is a replayable projection operation, not a replacement for lifecycle history.

## 3. Goals

1. Define an explicit lifecycle graph with no rank-based or inferred transitions.
2. Advance document status, current stage, update time, and version deterministically.
3. Preserve append-only lifecycle events as audit truth.
4. Make duplicate event replay and stale-version behavior explicit.
5. Centralize policy so all v0.13 writers use the same rules.
6. Preserve repository, Query Facade, API, and Streamlit boundaries.
7. Verify identical in-memory and SQLite behavior.
8. Keep errors and projection metadata privacy-safe.

## 4. Non-Goals

- Public mutation endpoints or Streamlit write actions.
- Runtime producer adapters or real reprocess execution.
- New API paths, response envelopes, or UI components.
- Cross-record distributed transactions or an outbox.
- Authentication, authorization, tenants, OCR, LLM, or external services.
- Raw document, row, correction, artifact, or storage-path persistence.
- Replacing processing, review, or reprocess records with document status values.

## 5. Package Location Decision

### Selected: `src/document_state/lifecycle/`

Lifecycle transition policy and projection consistency are Document State invariants used by multiple writers. A dedicated package keeps policy independent of ingestion, processing, review, and workflow writers and allows deterministic policy testing without repository access.

### Rejected: `src/document_state/writers/lifecycle.py`

Embedding policy in the writer package would blur event append and projection responsibilities and encourage each writer to evolve different rules. Writers should delegate to a public lifecycle port.

### Rejected: `src/workflow_runtime/lifecycle/`

Workflow Runtime does not own ingestion or review lifecycle state. Locating the policy there would invert the established dependency boundary and encourage direct persistence imports.

## 6. Advancement Model Decision

Use a dedicated `LifecycleAdvancementService` with an immutable policy catalog.

- The policy layer is pure: given current status, target status, and bounded context, it returns an allowed transition or a stable rejection.
- The service receives injected Document State read/write ports and never selects a backend.
- The service updates only the mutable `DocumentRecord` projection.
- v0.13 writers remain responsible for constructing and idempotently appending lifecycle events.
- Phase 3 integrates writers through a narrow `LifecycleAdvancementPort`; writers do not duplicate policy.

Writer ordering is audit-first:

1. Load the document and prevalidate the requested transition.
2. Append the lifecycle event with its existing deterministic idempotency key.
3. Advance the document snapshot with `expected_version` compare-and-swap.
4. Return success, no-op, conflict, rejection, or projection-pending using bounded codes.

If step 3 fails after step 2, history remains truthful and the same event can be replayed to repair the projection. v0.14 does not claim cross-record atomicity.

## 7. Canonical Lifecycle State Model

The v1 document projection uses the existing `DocumentStatus` values:

```text
received
ingested
classified
parsed
extracted
transformed
validated
matched
review_required
approved
export_ready
exported
failed
```

No new API-visible status is required in v1:

- `processing` is represented by `ProcessingSnapshot.status` plus `DocumentRecord.current_stage`.
- `structured` canonicalizes to the existing `parsed` status.
- `reprocess_planned` remains a `ReprocessPlanRecord`; it does not advance the document by itself.
- processing/review `skipped` remains a processing or review outcome. It does not invent a document status or silently mark a document complete.

This preserves v0.9 status filters and payload meanings.

### Normal Progression

The catalog uses explicit edges, including necessary legacy-short-path edges:

- `received -> ingested | classified | failed`
- `ingested -> classified | parsed | failed`
- `classified -> parsed | extracted | failed`
- `parsed -> extracted | transformed | validated | review_required | failed`
- `extracted -> transformed | validated | review_required | failed`
- `transformed -> validated | review_required | failed`
- `validated -> matched | review_required | approved | export_ready | failed`
- `matched -> review_required | approved | export_ready | failed`
- `review_required -> approved | failed`
- `approved -> export_ready | exported | failed`
- `export_ready -> exported | failed`

Any non-terminal status may transition to `failed` through an explicit safe failure event. The catalog does not infer progress from string order or stage names.

### Terminal And Control Behavior

- `exported` is terminal and rejects all later document-status transitions.
- `failed` is terminal for ordinary progress. Recovery requires a valid linked `ReprocessPlanRecord` for the same document and an explicitly approved recovery edge.
- Reprocess planning alone leaves the current document status unchanged. When future execution begins, the first resumed lifecycle event carries the plan ID and may move `failed` or `review_required` to the catalogued target stage status.
- In v1, allowed recovery targets are `classified`, `parsed`, `extracted`, `transformed`, `validated`, `matched`, or `approved`; a later service must verify that linked recovery context governs the same target.
- A skipped processing stage leaves the document at its last approved lifecycle status. A skipped or rejected review requires an explicit policy-owned outcome event; it is never inferred from review metadata.
- Same-status events are idempotent projection no-ops. Their append-only history remains available, but they do not increment the document version.
- Backward transitions without valid recovery context are rejected as `invalid_transition`.

## 8. Proposed Contracts

Phase 1 defines immutable, JSON-compatible contracts:

- `LifecycleTransitionDefinition`: current state, target state, transition kind, terminal/recovery flags.
- `LifecycleAdvancementRequest`: lifecycle event, expected document version, optional reprocess plan ID.
- `LifecycleAdvancementPlan`: document ID, event ID, from/to status, source stage, expected/new version, updated timestamp, and outcome intent.
- `LifecycleAdvancementResult`: status (`advanced`, `already_applied`, `rejected`, `conflict`, `not_found`, `source_unavailable`, `projection_pending`), safe code, document ID, event ID, and versions.
- `LifecycleAdvancementError`: stable codes only; no payload or source exception.
- `LifecycleAdvancementPort`: read-only method surface from writer perspective.

The request references a validated `DocumentLifecycleEvent`; it does not contain document data, rows, artifacts, or arbitrary runtime results.

Phase 1 implements these contracts as immutable JSON-compatible values under `src/document_state/lifecycle/`, together with stable result/error contracts, the existing-status state catalog, deterministic candidate ordering, explicit recovery policy, and pure evaluation functions. It performs no repository calls, document updates, writer integration, API/UI changes, or service implementation.

Phase 2 implements `LifecycleAdvancementService` over explicitly injected narrow document read/write repository ports. It performs policy validation, same-state replay detection, optimistic `DocumentRecord` replacement, safe repository-error mapping, and explicit conflict versus projection-pending outcomes. A backward-compatible optional `source_stage` request field supplies the projected current stage. The service works with in-memory and SQLite compositions without selecting or importing either backend and does not append lifecycle events or integrate writers.

## 9. Idempotency And Ordering

- Lifecycle append idempotency remains owned by v0.13 writer/repository behavior.
- Projection idempotency is status-aware: if the document already has the event's target status or a later valid state, replay returns a deterministic no-op rather than incrementing version.
- Older backward events are rejected/no-op according to policy and never regress the snapshot.
- Same event ID with conflicting event content remains a repository conflict.
- Event ordering uses existing deterministic lifecycle ordering `(occurred_at, event_id)` for reconciliation and tests.
- `updated_at` comes from the accepted lifecycle event; clocks are not sampled inside the service.
- `current_stage` comes from bounded `source_stage`, never arbitrary metadata.

## 10. Expected Version Strategy

- Every advancement request carries the document version observed during planning.
- A successful update writes exactly `expected_version + 1` through `update_document`.
- The service never applies last-write-wins and never silently substitutes a newer version.
- A stale version returns `conflict` or `projection_pending` after event append.
- The caller reloads the document and replays the same event. The service then either advances it, reports already applied/later state, or rejects it under the current policy.
- Same-status replay does not write or increment version.

## 11. Failure Handling

- **Missing document:** reject before append where possible; return `not_found` without sensitive context.
- **Invalid transition:** no snapshot update; prevalidation prevents append in the ordinary path.
- **Duplicate lifecycle replay:** append idempotency returns the existing event; projection returns `already_applied` or safely catches up.
- **Stale version:** event may already be committed; return bounded `projection_pending` and permit explicit replay.
- **Repository unavailable:** map to `source_unavailable`; do not include driver errors, SQL, paths, or tracebacks.
- **Unexpected repository error:** map to `internal_error`; preserve only safe IDs/codes.
- **Concurrent valid events:** one compare-and-swap wins. The loser reloads and is re-evaluated against the new state.

## 12. Writer Integration

Phase 3 adds optional explicit lifecycle advancement injection to the v0.13 writers that append lifecycle events. The integration becomes required only in an owner-approved composition path; writers do not construct the service.

- `IngestionDocumentStateWriter`: advances `received`, `ingested`, and `classified` events.
- `ProcessingDocumentStateWriter`: advances approved parse/extract/transform/validate/match/failure events when commands exist.
- `ReviewDocumentStateWriter`: advances `review_required`, approved outcome, and reprocess-linked recovery events.
- `WorkflowDocumentStateWriter`: advances only explicit lifecycle commands, never workflow status by inference.

No writer derives document state from processing metadata, review metadata, or raw runtime results.

Phase 3 implements this integration through the shared append helper. With a service injected, writers pre-read and prevalidate policy, append the lifecycle event idempotently, then advance with `lifecycle_event_persisted=True`. Without injection, all legacy append behavior remains unchanged. Processing accepts explicit `parsed`, `validated`, and `matched` events; review accepts `review_required` and `approved`; workflow accepts `exported` and `failed`; ingestion retains `received` and `classified`. Reprocess planning remains a separate record and never invents a document status.

## 13. Read Projection Impact

- Document list/detail status changes automatically because `DocumentStateQueryFacadeAdapter` already maps `DocumentRecord.status`.
- `current_stage`, `updated_at`, and version reflect the latest accepted advancement.
- Processing status continues to come from processing snapshots; it is not synthesized from document status.
- Review queue visibility continues to come from review records. A `review_required` document status may be used for consistency assertions, not as a replacement for review state.
- Existing API paths, envelopes, filters, pagination, request IDs, security headers, and successful payload shapes remain unchanged.
- Streamlit `api_preview` displays the updated API document status without UI changes.

## 14. Privacy And Safety

- No raw documents, rows, correction values, artifact payloads, storage paths, credentials, raw exceptions, or stack traces enter policy requests, results, logs, or metadata.
- Errors contain only stable codes and bounded field/status identifiers.
- Reprocess validation reads only safe plan identity, document identity, and target-stage fields.
- The service preserves existing allowlisted scalar metadata and does not copy event metadata wholesale into the document record.

## 15. Backend Compatibility

The service depends on Document State repository Protocols only. Both in-memory and SQLite backends already support immutable reads and optimistic `update_document`. No database-specific branch, silent fallback, API wiring, or persistence import is permitted.

## 16. Testing Strategy

- Pure transition-catalog tests for every allowed, terminal, failure, recovery, same-state, and invalid edge.
- Contract immutability, JSON compatibility, and privacy rejection tests.
- Service tests for success, no-op replay, stale version, missing document, invalid transition, and unavailable source.
- Shared in-memory/SQLite tests for identical versions and projections.
- Concurrent same-version advancement tests without sleeps.
- Writer integration tests proving append-then-advance ordering and partial retry repair.
- Read-after-advance tests through repositories, Query Facade, API provider, and Streamlit API-provider shapes.
- Existing Document State, writer, Query Facade, API, UI, Review, boundary, and full regressions.

## 17. Implementation Phases

1. **Lifecycle transition contracts and policy catalog:** immutable contracts, safe errors/results, explicit graph, terminal/recovery rules, and pure tests.
2. **Lifecycle advancement service:** repository-injected compare-and-swap projection service with replay and safe failure behavior.
3. **Writer integration:** inject the lifecycle port into applicable v0.13 writers and verify audit-first partial-retry behavior.
4. **Read-after-advance verification:** prove backend parity and updated Query Facade/API/Streamlit projections without endpoint or UI changes.
5. **Release closure:** focused/full verification, summary, handoff, release notes, and milestone documentation.

## 18. Risks And Open Questions

- **Append/update split:** a committed lifecycle event can temporarily lead its snapshot. Replay repairs it; a future unit-of-work/outbox may reduce this window.
- **Concurrent event ordering:** CAS prevents lost updates, but competing events require deterministic re-evaluation and may leave a rejected event in history after a race.
- **Recovery authorization:** v0.14 can validate an existing safe reprocess plan but does not execute it or establish public authorization.
- **Legacy missing events:** shortcut edges are intentionally narrow; migration/backfill of historical lifecycle data is deferred.
- **Skipped document disposition:** current contracts model skipped processing/review, not a document terminal status. Adding one requires a separate contract decision.
- **Projection rebuild:** full batch rebuild tooling is deferred; v1 supports deterministic single-event replay and test reconstruction.

## 19. Definition Of Done

- One explicit lifecycle policy governs all snapshot advancement.
- Append-only history remains unchanged and authoritative.
- Document snapshots advance deterministically with compare-and-swap versions.
- Duplicate replay, stale versions, invalid transitions, missing documents, and unavailable repositories behave safely.
- Recovery requires linked reprocess context and cannot silently regress state.
- In-memory and SQLite results are equivalent.
- Query Facade, API, and Streamlit read updated status without contract or UI changes.
- Privacy and runtime boundaries remain compliant.
- Release documentation and full verification are complete.

## 20. Release Readiness Criteria

- All focused lifecycle, writer, repository, Query Facade, API/UI, Review, and boundary suites pass.
- Full regression passes with known generated files restored.
- No API/UI mutation path or backend selection is introduced.
- Transition catalog and recovery behavior are documented and exhaustively tested.
- Recommended tag is prepared but not created by Codex.
