# Upload-to-Processing Writer Integration v1 Plan

**Milestone:** v0.13
**Status:** Accepted; Phases 1-4 implemented

## 1. Problem Statement

v0.12 provides durable Document State repositories and explicit backend composition, but real upload, ingestion, workflow, validation, matching, and review outcomes do not write operational state into those repositories. API and Streamlit can read repository-backed projections, yet the durable path is not populated by runtime activity.

v0.13 adds an internal writer boundary that translates approved runtime outcomes into privacy-safe Document State records. It does not add public mutation endpoints, upload UI, raw blob storage, or production database infrastructure.

## 2. Current And Target Architecture

Current read path:

```text
Document Intelligence API
  -> FacadeDocumentIntelligenceProvider
  -> Workflow Query Facade
  -> DocumentStateQueryFacadeAdapter
  -> Document State repositories
  -> DocumentStateComposition
  -> SQLite durable backend OR in-memory backend
```

Target read-after-write path:

```text
Upload / ingestion / processing producer
  -> producer-side result adapter
  -> Document State writer command
  -> Document State writer service
  -> injected Document State read/write ports
  -> in_memory OR sqlite
  -> DocumentStateQueryFacadeAdapter
  -> Workflow Query Facade
  -> Document Intelligence API
  -> Streamlit api_preview
```

The API and Streamlit remain read-only consumers. Runtime producers do not select a backend; a composition root selects `in_memory` or `sqlite` and injects the resulting ports.

## 3. Goals

1. Define a stable internal command boundary for Document State writes.
2. Create document records and append lifecycle history from upload/ingestion outcomes.
3. Persist processing snapshots, validation issues, matching summaries, review references, correction summaries, reprocess plans, workflow runs, and audit events.
4. Preserve deterministic IDs, ordering, retries, optimistic versions, and append idempotency.
5. Keep runtime-specific payloads outside Document State writers.
6. Preserve Document State privacy validation and opaque artifact references.
7. Support both in-memory and SQLite repositories through injected ports.
8. Verify end-to-end read-after-write visibility through the existing Query Facade and API provider boundary.

## 4. Non-Goals

- Public POST, PUT, PATCH, or DELETE endpoints.
- Streamlit upload processing or state mutation.
- Authentication, authorization, tenant isolation, or rate limiting.
- PostgreSQL/Supabase implementation or production provisioning.
- Raw document, row, artifact, OCR, or LLM payload storage.
- Encrypted blob-store implementation.
- External services, event bus, distributed transaction, or general workflow redesign.
- Automatic production backend activation.
- Competitor-price or legacy API/dashboard integration.

## 5. Package Location Decision

### Selected: `src/document_state/writers/`

This package owns the invariant being protected: transforming normalized write commands into valid Document State records and repository operations. It keeps idempotency, versioning, privacy projection, and failure semantics beside the repository contracts they govern.

The package must import only standard library and public/package-local Document State modules. It must not import Document Engine, Workflow Runtime implementation modules, Matching Runtime, Review Runtime, API, UI, storage, telemetry, or external services.

Producer-specific translation stays at producer boundaries, for example:

```text
src/document_engine/integrations/document_state.py
src/workflow_runtime/integrations/document_state.py
src/review_runtime/integrations/document_state.py
```

These adapters may import their producer's public result contracts plus public writer commands. They must emit normalized commands, not invoke concrete repositories or choose a backend.

### Rejected: `src/workflow_runtime/writers/document_state/`

Workflow Runtime does not own upload ingestion or Review Runtime outcomes. Locating all writers there would make Workflow Runtime a cross-runtime persistence coordinator and encourage direct imports of unrelated internals.

### Rejected: `src/ingestion_runtime/document_state_writers/`

No standalone ingestion runtime currently exists, and the scope includes workflow, validation, matching, review, correction, reprocess, and audit outcomes. Creating a runtime solely to host cross-domain writers would assign misleading ownership.

## 6. Writer Contracts

Writer commands are immutable, JSON-compatible, bounded, and backend-neutral. Proposed command families:

- `DocumentIngestionWrite`: document identity, filename, classified document type, confidence, ingestion identity, source runtime/stage, timestamps, status progression, and optional opaque artifact reference.
- `ProcessingSnapshotWrite`: document ID, workflow run ID, stage, safe status, timing, duration, expected version, and safe metadata.
- `ValidationIssuesWrite`: document/validation run identity plus ordered privacy-safe issue summaries.
- `MatchingSummariesWrite`: document/matching run identity plus ordered candidate summaries without entity payloads.
- `ReviewSummaryWrite`: review case reference, reason, priority, status, assignment, counts, decision/reprocess state, timestamps, and expected version.
- `CorrectionSummariesWrite`: field path, operation, reason code, actor, source stage, and time; no old/new values.
- `ReprocessPlansWrite`: stage references, counts, reason, actor, mode, and timestamp; no artifact payloads.
- `WorkflowRunWrite`: workflow/run identity, safe state, timings, stage counts, current stage, and expected version.
- `AuditEventsWrite`: allowlisted event type, actor, scoped IDs, timestamp, and scalar safe metadata.

Commands carry required stable IDs rather than generating random IDs inside repository services. Producer adapters may derive deterministic IDs from trusted source event IDs using a fixed namespace and documented canonical fields.

Phase 1 implements these contracts under `src/document_state/writers/` as immutable commands, safe errors/results, deterministic idempotency helpers, a fixed mapping catalog, and structural internal writer ports. It performs no repository writes and imports no runtime, persistence-engine, API, or UI implementation.

Phase 2 implements `IngestionDocumentStateWriter` with explicitly injected Document State read/write repository ports. It supports replay-safe document creation, received/classified lifecycle appends, classification processing snapshot create/update, and optional safe ingestion audit events against either active repository backend. It does not select a backend or import producer, API, UI, Query Facade, or persistence-engine implementations.

Phase 3 implements processing, validation, matching, review, correction, reprocess, workflow-run, lifecycle, and audit writer services over the same injected repository boundary. Append-only records use deterministic keys, mutable records use read-compare-create and explicit expected versions, and bounded partial failures can be retried without duplicate persisted records.

Phase 4 verifies the complete writer-to-read path with deterministic fixtures against both active backends. In-memory and reconstructed SQLite state produce equivalent Workflow Query Facade and API-provider projections; replay, filters, pagination, privacy projection, v0.9 payload shapes, and GET-only API behavior remain intact without production-module changes.

## 7. Runtime Output Mapping

### Upload And Document Engine

- Upload acceptance creates `DocumentRecord(status=received, current_stage=received)` and a `received` lifecycle event.
- `DocumentIngestionResult.ingestion_id` becomes lineage/idempotency input, never a raw payload container.
- Source filename is reduced to a bounded display filename; full paths are not persisted.
- Classification label/confidence map to document type/confidence only after allowlist validation.
- Successful load/normalize maps to `ingested`; classification maps to `classified`.
- Parsing completion maps to `parsed`; structural validation creates safe issue summaries and advances to `validated`, `review_required`, or `failed` according to explicit policy.

The producer adapter must never call `DocumentIngestionResult.to_dict()` and pass it wholesale because that representation contains document content and source paths.

### Workflow Runtime

- `WorkflowResult` maps to one `WorkflowRunRecord` and ordered stage snapshot commands.
- `StageResult.stage_name`, status, duration, and bounded safe metadata map to `ProcessingSnapshot`.
- `StageResult.output_artifact` is never passed to Document State.
- Raw `StageResult.error` is not persisted; adapters map known failures to fixed error/reason codes and safe templates.
- Successful transform, validation, matching, approval/export stages advance document lifecycle only through an explicit stage-to-status catalog.

### Validation And Matching

- Validation results map rule ID, field, severity, code, safe message template, and occurrence time. Full rows and failed values are excluded.
- Matching results map candidate ID, entity type, confidence, status, and run identity. Request entity data, master records, and candidate payloads are excluded.
- Deterministic ordering is applied before stable issue/match IDs and append keys are derived.

### Review Runtime

- Review cases map to `ReviewReferenceRecord` summaries.
- Decisions update review summary versions and append safe audit events.
- Corrections map field path, operation, reason, actor, time, and stage only; old/new values never cross the writer boundary.
- Declarative reprocess plans map stage names and artifact counts only. Artifact lists and payloads remain outside Document State.

## 8. Idempotency Strategy

Every command includes a bounded source event identity. Domain-separated append keys are deterministic:

```text
document:{document_id}:lifecycle:{source_event_id}:{status}
validation:{validation_run_id}:{issue_id}
matching:{matching_run_id}:{match_id}
correction:{review_case_id}:{correction_id}
reprocess:{review_case_id}:{plan_id}
audit:{event_id}
```

- Identical append retry returns the existing record.
- Reusing a key or stable ID with different canonical content returns safe `conflict`.
- Initial document/workflow/review create retries use read-compare-create: identical existing safe records are accepted; differing records conflict.
- A create race retries the comparison after a conflict rather than treating every duplicate as success.
- Random IDs, timestamps generated during retry, and iteration-order-dependent keys are prohibited.

## 9. Versioning Strategy

- Mutable document, processing, review, and workflow snapshots require caller-visible `expected_version`.
- Updates write records at exactly `expected_version + 1` through existing compare-and-swap ports.
- The writer does not silently overwrite, auto-retry with a new version, or apply last-write-wins.
- A stale version returns safe conflict. The producer may reload through an injected read port, recompute intentionally, and issue a new command.
- Lifecycle, validation, matching, correction, reprocess, and audit records remain append-only.

## 10. Failure And Consistency Model

Existing repositories guarantee one operation per transaction, not a cross-record unit of work. v0.13 therefore uses ordered, replay-safe checkpoints:

1. Validate the complete command batch and privacy projection before the first write.
2. Create or compare the mutable parent snapshot.
3. Append deterministic lifecycle/domain events.
4. Update the current snapshot with an explicit expected version.
5. Append a safe audit event only after its corresponding state write succeeds.

If a later operation fails, earlier committed operations remain. The service returns a bounded result containing committed operation IDs/counts and a safe failure code. Retry resumes with the same IDs and keys. It does not delete history or fabricate rollback events.

Cross-record atomic transactions, outbox delivery, and distributed exactly-once guarantees remain deferred. SQLite transaction internals must not leak into writer contracts.

## 11. Artifact Reference And Privacy Strategy

- Commands may carry `ArtifactReference(artifact_ref_id, artifact_kind, source_stage)` with opaque bounded identifiers only.
- No storage path, URL with credentials, document bytes/text, row data, extracted fields, candidate payload, correction value, OCR output, or arbitrary artifact is accepted.
- Persistence uses explicit record fields where available and narrowly allowlisted scalar metadata keys such as `artifact_ref_id` and `artifact_kind` only after privacy review.
- References do not imply that Document State owns artifact storage or access control.
- Raw encrypted blob storage remains a separate future boundary with independent auth, retention, audit, and deletion policy.

## 12. Composition And Dependency Injection

The application composition root performs backend selection once:

```text
composition = compose_document_state(validated_config)
writer_service = DocumentStateWriterService(
    reader=composition.reader,
    writer=composition.writer,
)
```

Producer adapters receive the writer service explicitly. They cannot call `compose_document_state`, inspect environment variables, or fall back between backends. Both active v0.12 backends remain supported for tests/local development.

## 13. Read-After-Write Integration

End-to-end verification must prove:

```text
deterministic producer result
  -> normalized writer command
  -> injected writer service
  -> in_memory and sqlite repositories
  -> DocumentStateQueryFacadeAdapter
  -> Workflow Query Facade read models
  -> FacadeDocumentIntelligenceProvider
  -> existing GET response shapes
```

No route, response envelope, payload meaning, request ID, security header, Streamlit mode, or UI component changes are required. Streamlit `api_preview` observes state only through the existing API read path.

## 14. Testing Strategy

- Contract serialization, immutability, bounded fields, and forbidden payload rejection.
- Deterministic mapping fixtures for Document Engine, Workflow, validation, matching, and Review outcomes.
- Writer behavior against both in-memory and SQLite compositions.
- Retry parity, duplicate/conflicting keys, stale versions, partial failure, and replay completion.
- Input/result immutability and proof that artifacts/raw values never reach repositories.
- End-to-end read-after-write parity through Query Facade and API provider projections.
- Recursive import checks for writer and producer adapter boundaries.
- Existing Document State, Query Facade, API, Streamlit, Review, boundary, and full regressions.

## 15. Runtime Boundaries

- `document_state.writers` imports only standard library and public/package-local Document State modules.
- Producer adapters import their own public contracts and public writer commands only.
- Writers receive repository ports; they do not import SQLite or in-memory concrete classes.
- API and Streamlit remain read-only and never receive write ports.
- Workflow Query Facade remains read-only and imports no writers or persistence modules.
- No writer imports legacy storage, telemetry internals, FlowSync, competitor-price modules, OCR, LLM, or external services.

## 16. Risks And Open Questions

- **Cross-record partial writes:** use deterministic replay now; consider a unit-of-work/outbox milestone later.
- **Create idempotency needs reads:** inject the read port narrowly for compare-after-conflict; do not weaken duplicate conflict semantics.
- **Stage/status ambiguity:** approve a fixed mapping catalog rather than infer lifecycle from arbitrary stage names.
- **Unsafe existing errors/metadata:** translate to fixed codes and allowlisted summaries; never persist raw exception text.
- **Artifact reference ownership:** agree on opaque ID format before adding metadata allowlist keys.
- **Producer coupling:** keep runtime-specific imports in producer adapters, not Document State writer services.
- **Timestamp/ID determinism:** require source timestamps and event IDs; define behavior for legacy outputs that lack them.
- **Review duplication:** decide whether Review Runtime emits commands synchronously or through a later outbox; v0.13 plans synchronous internal calls only.

## 17. Definition Of Done

- Internal writer contracts and services cover all ten Document State record families.
- Upload/ingestion and processing outputs map without raw payload leakage.
- Retry, conflict, version, failure, and replay behavior is deterministic and tested.
- Both in-memory and SQLite compositions pass writer integration tests.
- Read-after-write state is visible through existing Query Facade/API read contracts.
- API/Streamlit remain read-only; no endpoint or UI change is introduced.
- Runtime and persistence boundaries remain compliant.
- Documentation, handoff, release notes, and full regression verification are complete.

## 18. Release Readiness Criteria

- Focused writer, Document State, Query Facade, API, Streamlit, Review, and boundary suites pass.
- Full regression passes with known generated files restored.
- No raw content, row, correction value, artifact payload, stack trace, or storage path appears in persisted records.
- No API/UI write path or silent backend selection exists.
- Recommended tag is prepared but not created by Codex.
