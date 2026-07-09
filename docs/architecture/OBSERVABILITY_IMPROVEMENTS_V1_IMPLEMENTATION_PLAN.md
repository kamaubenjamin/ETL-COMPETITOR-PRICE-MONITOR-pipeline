# Observability Improvements v1 Implementation Plan

Date: 2026-07-09
Status: Planned
Milestone: v0.5 Runtime Hardening
Architecture plan: `docs/architecture/OBSERVABILITY_IMPROVEMENTS_V1_PLAN.md`

## Scope

Observability Improvements v1 adds passive runtime observability only.

In scope:

- Repository-owned event, metric, trace, and error contracts.
- Fail-open sink foundation.
- Workflow Runtime instrumentation.
- Entity Runtime instrumentation.
- Matching Runtime instrumentation.
- Tests for contracts, sinks, privacy, correlation, and regression behavior.
- Documentation, ADR, release notes, summary, and handoff.

Out of scope:

- Dashboard UI.
- External monitoring vendor integration.
- OpenTelemetry exporter.
- Alerting engine.
- Synchronous dependency on Monitoring Runtime.
- Runtime behavior changes beyond passive instrumentation.

## Phase Breakdown

### Phase 1: Contracts + ADR

Purpose:

Define the neutral observability contract surface and document the architectural decision before runtime instrumentation begins.

Tasks:

1. Create ADR-011 for passive runtime observability.
2. Create the observability package/module boundary.
3. Define `RuntimeTraceContext`.
4. Define `RuntimeErrorRecord`.
5. Define `RuntimeEvent`.
6. Define `RuntimeMetric`.
7. Define event status, severity, metric type, and runtime name enumerations.
8. Define event name and metric name registries.
9. Define allowed metric dimensions.
10. Define privacy allowlists and sanitization rules.
11. Add unit tests for contract construction, validation, and serialization.

Acceptance criteria:

- Contracts can be imported without importing Workflow, Entity, Matching, Document, Review, API, or Monitoring Runtime internals.
- Contracts serialize to plain dictionaries suitable for JSON output.
- Required fields are enforced.
- Invalid statuses, severities, metric types, or disallowed dimensions are rejected or sanitized according to implementation choice.
- ADR records why v1 is passive and vendor-neutral.

### Phase 2: Sink Foundation

Purpose:

Add a minimal fail-open sink layer for local capture and tests.

Tasks:

1. Define `ObservabilitySink` interface or protocol.
2. Implement `NoOpObservabilitySink`.
3. Implement `InMemoryObservabilitySink`.
4. Implement optional `JsonlObservabilitySink` for local debugging.
5. Add helper emitter that wraps sink calls and suppresses sink errors.
6. Add default sink selection with no-op behavior.
7. Add tests for no-op, in-memory, JSONL if included, and sink failure suppression.

Acceptance criteria:

- Observability is disabled/no-op by default.
- Tests can inject an in-memory sink.
- Sink exceptions do not escape to runtime callers.
- No sink requires network access.
- JSONL output, if implemented, writes sanitized contract records only.

### Phase 3: Workflow Runtime Instrumentation

Purpose:

Instrument the runtime orchestration layer first because it owns workflow and stage lifecycle context.

Tasks:

1. Create or accept trace context when a workflow run starts.
2. Propagate trace context through stage execution.
3. Emit workflow run started, succeeded, and failed events.
4. Emit workflow stage started, succeeded, failed, skipped, and retried events where applicable.
5. Emit lock acquisition started, succeeded, and failed events.
6. Emit lock release, lease renewal, lease expiry, stale lease recovery, idempotency, and fallback provider events where applicable.
7. Emit workflow and stage duration metrics.
8. Emit lock contention, lock acquisition duration, lease recovery, and idempotency duplicate metrics.
9. Add unit and integration tests around emitted events and correlation propagation.
10. Confirm existing Workflow Runtime tests pass with default no-op observability.

Acceptance criteria:

- Workflow run events share the same `correlation_id` and `trace_id`.
- Stage events have parent-child trace relationships.
- Locking and idempotency instrumentation does not change lock semantics.
- Existing workflow behavior is unchanged when observability is disabled.

### Phase 4: Entity + Matching Instrumentation

Purpose:

Instrument hardened entity write paths and deterministic matching decisions without leaking domain payloads.

Entity Runtime tasks:

1. Accept optional trace context from Workflow Runtime or create local context.
2. Emit entity write started, succeeded, and failed events.
3. Emit optimistic write attempted events.
4. Emit CAS conflict events and metrics.
5. Emit pessimistic lock escalation events and metrics.
6. Emit lease acquired, renewed, expired, and released events where applicable.
7. Emit entity idempotency duplicate events and metrics.
8. Emit graceful degradation events where applicable.
9. Add tests for entity write observability and sink failure suppression.

Matching Runtime tasks:

1. Accept optional trace context from Workflow Runtime or create local context.
2. Emit matching decision created events.
3. Emit candidate count metrics.
4. Emit match strategy attributes using allowlisted strategy names.
5. Emit low-confidence and no-match events.
6. Emit matching decision count and low-confidence metrics.
7. Add tests that no raw candidate/entity values are emitted.

Acceptance criteria:

- Entity observability covers write, conflict, escalation, lease, and idempotency paths.
- Matching observability covers decision and confidence paths.
- Entity and Matching instrumentation do not require Monitoring Runtime.
- No sensitive entity or document values are emitted.

### Phase 5: Verification + Release

Purpose:

Verify behavior, update governance artifacts, and close the milestone.

Tasks:

1. Run contract and sink unit tests.
2. Run workflow observability tests.
3. Run entity observability tests.
4. Run matching observability tests.
5. Run privacy tests.
6. Run runtime boundary verification.
7. Run relevant regression tests for workflow, entity, matching, and contracts.
8. Create summary and handoff documentation.
9. Create release notes.
10. Update `docs/ROADMAP.md`.
11. Update `TECHNICAL_DEBT.md`.
12. Update `docs/AGENT_CONTEXT.md` if milestone status remains stale.
13. Commit, push, and tag after implementation verification is complete.

Acceptance criteria:

- All required observability tests pass.
- Existing runtime regression tests pass or any unrelated known failures are documented.
- Boundary verification remains clean.
- Documentation is sufficient for a future agent to continue without chat history.
- Milestone is closed only after commit, push, and tag.

## Files To Create

Architecture and governance:

- `docs/architecture/OBSERVABILITY_IMPROVEMENTS_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/OBSERVABILITY_IMPROVEMENTS_V1_SUMMARY.md`
- `docs/architecture/OBSERVABILITY_IMPROVEMENTS_V1_HANDOFF.md`
- `docs/adr/ADR-011-observability-improvements.md`
- `docs/releases/v0.5-observability-improvements.md`

Runtime contracts and sinks:

- `src/observability/__init__.py`
- `src/observability/contracts.py`
- `src/observability/sinks.py`
- `src/observability/emitter.py`
- `src/observability/privacy.py`
- `src/observability/registry.py`

Tests:

- `tests/observability/__init__.py`
- `tests/observability/test_contracts.py`
- `tests/observability/test_sinks.py`
- `tests/observability/test_emitter.py`
- `tests/observability/test_privacy.py`
- `tests/workflow_runtime/test_workflow_observability.py`
- `tests/entity_runtime/test_entity_observability.py`
- `tests/test_matching_observability.py`

Optional local output support:

- No committed runtime output files should be created.
- If JSONL local output is implemented, generated `*.jsonl` observability files should be ignored or written only to temporary test paths.

## Files To Modify

Documentation:

- `docs/ROADMAP.md`
- `TECHNICAL_DEBT.md`
- `docs/AGENT_CONTEXT.md`
- `CHANGELOG.md`, if release notes are also tracked there.

Workflow Runtime candidates:

- `src/workflow_runtime/` modules that start workflow runs and execute stages.
- `src/workflow_runtime/locking/` modules that acquire/release locks, renew leases, perform idempotency checks, and select fallback providers.

Entity Runtime candidates:

- `src/entity_runtime/orchestration/orchestrator.py`
- `src/entity_runtime/concurrency/guard.py`
- `src/entity_runtime/concurrency/optimistic.py`
- `src/entity_runtime/concurrency/pessimistic.py`
- `src/entity_runtime/concurrency/leases.py`
- `src/entity_runtime/store/idempotency.py`
- `src/entity_runtime/store/version_store.py`

Matching Runtime candidates:

- Matching runtime module(s) that create match decisions and compute confidence.
- Existing matching tests may need small additions to assert emitted events without changing match behavior.

Boundary verification:

- Boundary exemption files should not need changes. If they do, the implementation must be reviewed as a boundary risk.

## Contracts

### RuntimeTraceContext

Required fields:

- `correlation_id`
- `trace_id`
- `span_id`
- `parent_span_id`
- `workflow_id`
- `workflow_run_id`
- `stage_name`
- `stage_run_id`
- `entity_version_key`
- `entity_id`
- `contract_name`
- `contract_version`

Implementation notes:

- Provide a constructor/helper for root workflow context.
- Provide a helper for child spans.
- Allow nullable runtime-specific fields.
- Do not require every runtime to know every field.

### RuntimeErrorRecord

Required fields:

- `error_code`
- `error_type`
- `message`
- `retryable`
- `root_cause`

Implementation notes:

- Messages must be sanitized.
- Full stack traces should not be emitted by default.
- Error codes should be stable enough for metrics and tests.

### RuntimeEvent

Required fields:

- `event_id`
- `event_type`
- `event_version`
- `timestamp`
- `runtime`
- `operation`
- `status`
- `severity`
- `trace`
- `duration_ms`
- `attributes`
- `error`

Implementation notes:

- `attributes` must be allowlisted.
- Event names should come from a registry or constants.
- Event objects should serialize cleanly to JSON-compatible dictionaries.

### RuntimeMetric

Required fields:

- `metric_name`
- `metric_type`
- `value`
- `unit`
- `timestamp`
- `runtime`
- `dimensions`
- `trace`

Implementation notes:

- Dimensions must be low-cardinality.
- Disallowed dimensions should be rejected or dropped consistently.
- Metric names should come from a registry or constants.

## Sink Design

### ObservabilitySink

Required methods:

- `emit_event(event)`
- `emit_metric(metric)`

Rules:

- Implementations should not mutate event or metric objects.
- Implementations should avoid blocking operations.
- Implementations must not require external services in v1.

### NoOpObservabilitySink

Purpose:

- Default sink.
- Drops all events and metrics.

Acceptance criteria:

- Safe for production-like execution without configuration.
- No side effects.

### InMemoryObservabilitySink

Purpose:

- Test sink.
- Stores emitted events and metrics in memory.

Acceptance criteria:

- Supports clearing captured records.
- Supports assertions by event type, metric name, runtime, and correlation ID.
- Not used as a production persistence mechanism.

### JsonlObservabilitySink

Purpose:

- Optional local development sink.
- Appends sanitized JSON records to a local JSONL file.

Acceptance criteria:

- Writes one event or metric per line.
- Uses only JSON-serializable contract output.
- Does not write raw payloads.
- Test output uses temporary paths.

### Emitter Helper

Purpose:

- Runtime-facing wrapper around a sink.
- Enforces fail-open behavior.

Rules:

- Catch sink exceptions.
- Never raise from an emit call by default.
- Optionally count suppressed sink failures internally.
- Preserve runtime execution flow.

## Runtime Integration Points

### Workflow Runtime

Primary integration points:

- Workflow run start/end.
- Stage execution start/end.
- Stage failure and retry handling.
- Lock provider acquisition and release.
- Lease renewal and recovery.
- Idempotency checks.
- Fallback provider selection.

Expected emitted records:

- `workflow.run.started`
- `workflow.run.succeeded`
- `workflow.run.failed`
- `workflow.stage.started`
- `workflow.stage.succeeded`
- `workflow.stage.failed`
- `workflow.lock.acquire.started`
- `workflow.lock.acquire.succeeded`
- `workflow.lock.acquire.failed`
- `workflow.lease.renewed`
- `workflow.idempotency.duplicate_detected`

### Entity Runtime

Primary integration points:

- Entity write orchestration.
- Version store reads/writes.
- Optimistic CAS attempts.
- CAS conflicts.
- Pessimistic lock escalation.
- Lease lifecycle.
- Idempotency checks.
- Graceful degradation paths.

Expected emitted records:

- `entity.write.started`
- `entity.write.succeeded`
- `entity.write.failed`
- `entity.cas.conflict`
- `entity.lock.escalated`
- `entity.lease.expired`
- `entity.idempotency.duplicate_detected`

### Matching Runtime

Primary integration points:

- Candidate generation.
- Match strategy selection.
- Match decision creation.
- Confidence scoring.
- Low-confidence and no-match results.

Expected emitted records:

- `matching.decision.created`
- `matching.low_confidence_detected`
- `matching.no_match_detected`

## Tests Required

Contract tests:

- Required fields are enforced.
- Valid records serialize to dictionaries.
- Invalid runtime names, statuses, severities, and metric types are rejected.
- Child spans preserve parent span IDs.
- Metrics reject or sanitize invalid dimensions.

Sink tests:

- No-op sink accepts events and metrics without side effects.
- In-memory sink captures events and metrics.
- In-memory sink can be cleared.
- JSONL sink writes valid JSON lines, if implemented.
- Emitter suppresses sink exceptions.

Workflow tests:

- Workflow run emits started and terminal events.
- Stage execution emits started and terminal events.
- Correlation ID is stable across workflow and stage events.
- Lock contention emits lock metrics.
- Idempotency duplicate emits duplicate events and metrics.
- Existing workflow behavior is unchanged with no-op sink.

Entity tests:

- Entity write emits started and terminal events.
- CAS conflict emits event and metric.
- Pessimistic escalation emits event and metric.
- Lease expiry/recovery emits event where applicable.
- Idempotency duplicate emits event and metric.
- Existing entity behavior is unchanged with no-op sink.

Matching tests:

- Match decision emits decision event.
- Candidate count emits metric.
- Low-confidence match emits event and metric.
- No-match emits event where applicable.
- Existing match results are unchanged with no-op sink.

Regression tests:

- Existing workflow runtime tests.
- Existing entity runtime tests.
- Existing matching runtime tests.
- Contract validation tests.
- Boundary verification tests.

## Privacy Tests

Required privacy test cases:

- Raw document text is not present in emitted events.
- OCR output is not present in emitted events.
- Raw entity values are not present in emitted events.
- Prices, supplier names, customer names, invoice numbers, ERP identifiers, and product names are not emitted unless explicitly sanitized and approved.
- Credentials, tokens, cookies, API keys, database URLs, and environment secrets are not emitted.
- Full stack traces are not emitted by default.
- Error messages are sanitized.
- Metric dimensions do not include raw document names, raw entity values, full exception messages, or unbounded free-form values.
- JSONL sink output contains only sanitized records.

Implementation guidance:

- Use explicit attribute allowlists.
- Add tests with deliberately sensitive fixture values and assert they are absent from serialized observability records.
- Prefer categories, counts, IDs, and stable codes over payload values.

## Boundary Verification

Required checks:

- Observability contracts do not import runtime internals.
- Workflow Runtime, Entity Runtime, and Matching Runtime may import neutral observability contracts and sinks.
- No runtime imports Monitoring Runtime.
- No Monitoring Runtime dependency is required to execute existing runtime tests.
- No new boundary exemption should be needed for observability.
- `scripts/verify_boundaries.py` should pass after implementation.

Boundary design rule:

Neutral observability modules are shared infrastructure. Runtime modules may emit to shared observability interfaces, but they must not call another runtime to record, store, display, or process observability data.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---:|---:|---|
| Observability code changes runtime behavior | Medium | High | Keep emit calls side-effect-light and fail-open; regression test no-op behavior. |
| Monitoring Runtime coupling slips in | Low | High | Boundary verification and ADR rule: no synchronous Monitoring Runtime dependency. |
| Sensitive values leak into observability records | Medium | High | Attribute allowlists, sanitization helpers, and privacy tests. |
| Event and metric names drift | Medium | Medium | Central registry/constants and tests. |
| Metric cardinality becomes unbounded | Medium | Medium | Dimension allowlist and validation. |
| Trace context becomes invasive | Medium | Medium | Pass optional metadata; create local context if absent. |
| JSONL sink creates unwanted repo diffs | Low | Medium | Use temp paths in tests and ignore local observability output if needed. |
| Scope expands into dashboarding or vendor integration | Medium | Medium | Keep v1 limited to passive contracts, sinks, and runtime instrumentation. |

## Definition of Done

This implementation plan is complete when:

- Phase 1 through Phase 5 are defined.
- Files to create and modify are identified.
- Contract shapes are specified.
- Sink behavior is specified.
- Runtime integration points are listed.
- Required tests are listed.
- Privacy tests are listed.
- Boundary verification requirements are listed.
- Risks and mitigations are documented.

The Observability Improvements v1 milestone is complete when:

- ADR-011 exists and is accepted.
- Runtime observability contracts are implemented and tested.
- Sink foundation is implemented and tested.
- Workflow Runtime emits passive observability records.
- Entity Runtime emits passive observability records.
- Matching Runtime emits passive observability records if retained in v1 implementation scope.
- Observability is no-op by default.
- Sink failures do not break runtime execution.
- Privacy tests prove sensitive payloads are not emitted.
- Boundary verification passes.
- Existing runtime regression tests pass or unrelated known failures are documented.
- Architecture, implementation, summary, handoff, release notes, roadmap, and technical debt docs are updated.
- Commit, push, and milestone tag are completed after verification.

End of document.
