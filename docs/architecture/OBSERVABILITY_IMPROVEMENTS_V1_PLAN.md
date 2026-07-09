# Observability Improvements v1 Plan

Date: 2026-07-09
Status: Planned
Milestone: v0.5 Runtime Hardening
Owner: Platform Architect
Implementation owner: Runtime Engineer
Governance owner: ETL Platform Governance

## Problem Statement

The platform has mature deterministic runtime layers and recent hardening for workflow locking and entity concurrency, but it does not yet have a consistent observability model. Runtime execution can be tested and inspected locally, yet future maintainers do not have a shared event, metric, trace, or correlation contract for understanding workflow progress, lock contention, entity write conflicts, matching decisions, or runtime failures.

Observability Improvements v1 establishes passive runtime observability for the Document Intelligence Platform. This milestone must improve auditability and operational diagnosis without adding dashboards, external monitoring vendors, or synchronous dependencies on a future Monitoring Runtime.

## Current Observability State

Current strengths:

- The roadmap identifies Observability Improvements as the next v0.5 Runtime Hardening objective after Workflow Runtime Locking and Entity Runtime Concurrency Hardening.
- Workflow Runtime Locking v1 provides lock providers, execution leases, idempotency keys, fallback behavior, and crash recovery, which are high-value observability sources.
- Entity Runtime Concurrency Hardening v1 provides versioned persistence, optimistic locking, pessimistic escalation, leases, idempotency protection, and graceful degradation, which are high-value observability sources.
- Matching Runtime already emphasizes deterministic, explainable match decisions.
- Runtime Boundary Verification Tier 1 exists and reinforces the need to preserve runtime isolation.
- Monitoring Runtime is recognized as a future runtime concept in agent context documentation.

Current gaps:

- No unified runtime event contract.
- No standard metric naming or dimensions.
- No trace context or correlation model across workflow runs, stages, entity writes, and matching decisions.
- No standard structured logging schema.
- No fail-open sink interface for passive event capture.
- No privacy rules for observability payloads.
- No implementation guidance for observing runtimes without creating runtime-to-monitoring coupling.

## Observability Principles

1. Passive by default.
   Runtime code may emit observability records, but observability must not control runtime behavior.

2. Fail-open.
   Observability failures must never fail workflow execution, entity writes, matching, or review handoff.

3. No synchronous Monitoring Runtime dependency.
   Existing runtimes must not synchronously call a Monitoring Runtime. Monitoring Runtime may consume emitted records in a later milestone.

4. No external vendor dependency in v1.
   v1 must use repository-owned contracts and local sinks only. Vendor or OpenTelemetry adapters can be added later behind the same sink boundary.

5. Runtime boundaries remain intact.
   Observability contracts are cross-cutting contracts, not permission for direct runtime coupling.

6. Structured, low-cardinality metrics.
   Metrics must be stable, named consistently, and avoid unbounded dimensions such as raw document names or free-form error text.

7. Correlation before dashboards.
   The first priority is traceability of a workflow run and its stage/entity/match operations, not visualization.

8. Privacy by design.
   Observability records must avoid raw document payloads, extracted values, credentials, customer secrets, and ERP data by default.

9. Deterministic and testable.
   Event emission and sink behavior must be deterministic enough to test without network access or external services.

## Event/Metric/Trace Contracts

Observability v1 should define repository-owned contracts for runtime events, metrics, trace context, and errors. These may be implemented as Python dataclasses or typed dictionaries in the implementation phase, but this plan defines the required shape.

### RuntimeEvent

Purpose: describe something that happened during runtime execution.

Required fields:

- `event_id`: unique event identifier.
- `event_type`: stable event name.
- `event_version`: schema version for the event shape.
- `timestamp`: UTC timestamp in ISO-8601 format.
- `runtime`: emitting runtime, such as `workflow`, `entity`, `matching`, `document`, `review`, `api`, or `monitoring`.
- `operation`: operation being observed.
- `status`: `started`, `succeeded`, `failed`, `skipped`, `retried`, `degraded`, or `blocked`.
- `severity`: `debug`, `info`, `warning`, `error`, or `critical`.
- `trace`: embedded `RuntimeTraceContext`.
- `duration_ms`: optional duration for completed operations.
- `attributes`: sanitized structured metadata.
- `error`: optional `RuntimeErrorRecord`.

Representative event types:

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
- `entity.write.started`
- `entity.write.succeeded`
- `entity.write.failed`
- `entity.cas.conflict`
- `entity.lock.escalated`
- `entity.lease.expired`
- `entity.idempotency.duplicate_detected`
- `matching.decision.created`
- `matching.low_confidence_detected`
- `contract.validation.failed`

### RuntimeMetric

Purpose: describe counters, gauges, and durations derived from runtime execution.

Required fields:

- `metric_name`: stable metric identifier.
- `metric_type`: `counter`, `gauge`, or `histogram`.
- `value`: numeric value.
- `unit`: unit such as `count`, `ms`, `ratio`, or `bytes`.
- `timestamp`: UTC timestamp in ISO-8601 format.
- `runtime`: emitting runtime.
- `dimensions`: low-cardinality tags.
- `trace`: optional `RuntimeTraceContext`.

Initial metric set:

- `workflow.run.count`
- `workflow.run.duration_ms`
- `workflow.run.failure.count`
- `workflow.stage.duration_ms`
- `workflow.stage.failure.count`
- `workflow.lock.contention.count`
- `workflow.lock.acquire.duration_ms`
- `workflow.lease.recovery.count`
- `workflow.idempotency.duplicate.count`
- `entity.write.count`
- `entity.write.duration_ms`
- `entity.cas.conflict.count`
- `entity.lock.escalation.count`
- `entity.lease.expiry.count`
- `entity.idempotency.duplicate.count`
- `matching.decision.count`
- `matching.low_confidence.count`
- `contract.validation.failure.count`

Allowed dimensions:

- `runtime`
- `operation`
- `status`
- `stage_name`
- `lock_provider`
- `entity_type`
- `match_strategy`
- `contract_name`
- `contract_version`
- `error_code`

Disallowed dimensions:

- Raw document text.
- Raw entity values.
- File contents.
- Customer secrets.
- Full exception messages.
- Unbounded IDs unless specifically approved for trace-only use.

### RuntimeTraceContext

Purpose: correlate events and metrics across a logical workflow execution.

Required fields:

- `correlation_id`: top-level correlation identifier.
- `trace_id`: end-to-end trace identifier.
- `span_id`: current operation span identifier.
- `parent_span_id`: parent operation span identifier, nullable.
- `workflow_id`: workflow definition identifier, nullable.
- `workflow_run_id`: workflow run identifier, nullable.
- `stage_name`: workflow stage name, nullable.
- `stage_run_id`: stage execution identifier, nullable.
- `entity_version_key`: entity write/version key, nullable.
- `entity_id`: canonical entity identifier, nullable and sanitized.
- `contract_name`: contract name, nullable.
- `contract_version`: contract version, nullable.

### RuntimeErrorRecord

Purpose: classify failures without leaking sensitive values.

Required fields:

- `error_code`: stable platform error code.
- `error_type`: exception or domain error category.
- `message`: sanitized short message.
- `retryable`: boolean.
- `root_cause`: optional sanitized category.

Disallowed fields:

- Stack traces by default.
- Raw payloads.
- Secrets, credentials, tokens, cookies, or environment values.
- Raw document text or extracted values.

## Correlation Model

Observability v1 introduces a correlation model that starts at the workflow run and flows down into stage execution, entity writes, and matching decisions.

Correlation hierarchy:

```text
correlation_id
  trace_id
    workflow_run_id
      stage_run_id
        entity_version_key
        matching_decision_id
```

Rules:

- `correlation_id` is the durable top-level identifier for one externally meaningful unit of work.
- `trace_id` groups all spans emitted while processing that unit of work.
- `span_id` identifies one operation.
- `parent_span_id` preserves execution hierarchy.
- Workflow Runtime creates or accepts the initial correlation context.
- Stage execution receives the current trace context.
- Entity Runtime and Matching Runtime may receive trace context as optional metadata.
- If no trace context exists, a runtime may create a local context rather than failing.
- Correlation metadata must not change domain semantics.

## Runtime Instrumentation Points

### Workflow Runtime

Initial instrumentation should prioritize Workflow Runtime because it orchestrates execution and can propagate trace context.

Required points:

- Workflow run started, succeeded, failed.
- Stage started, succeeded, failed, retried, skipped.
- Lock acquire started, succeeded, failed.
- Lock release succeeded, failed.
- Lease renewed, expired, recovered.
- Idempotency key accepted, duplicate detected, rejected.
- Fallback provider selected.

### Entity Runtime

Required points:

- Entity write started, succeeded, failed.
- Entity version read and write duration.
- Optimistic write attempted.
- CAS conflict detected.
- Pessimistic lock escalation triggered.
- Lease acquired, renewed, expired, released.
- Idempotency duplicate detected.
- Graceful degradation activated.

### Matching Runtime

Required points:

- Match decision created.
- Candidate count computed.
- Match strategy selected.
- Low-confidence result detected.
- No-match result detected.
- Historical match strategy used.

### Document Runtime

Recommended points:

- Document parse started, succeeded, failed.
- Section/table extraction counts.
- Parser fallback or degradation.

Document Runtime must not emit raw document contents in observability records.

### Review Runtime

Future points:

- Review item created.
- Review item assigned.
- Review decision recorded.
- Manual override applied.

Review Runtime is not required for v1 unless implementation scope expands.

### API Runtime

Future points:

- Request accepted.
- Request rejected.
- Response emitted.
- Contract validation failed.

API Runtime is not required for v1 unless implementation scope expands.

## Fail-Open Sink Architecture

Observability v1 should use a sink abstraction that receives events and metrics without creating a runtime dependency on any future Monitoring Runtime.

Required sink behavior:

- `emit_event(event)` accepts a `RuntimeEvent`.
- `emit_metric(metric)` accepts a `RuntimeMetric`.
- Sink errors are caught and suppressed by default.
- Sink failures may be counted internally but must not interrupt runtime execution.
- No network calls are required for v1.
- No external monitoring vendor integration is included in v1.

Initial sinks:

- `NoOpObservabilitySink`: default sink that drops records.
- `InMemoryObservabilitySink`: test sink for assertions.
- `JsonlObservabilitySink`: optional local development sink that appends sanitized records to a local JSONL file.

Sink selection:

- Default: no-op.
- Tests: in-memory.
- Local debugging: JSONL.
- Future Monitoring Runtime: asynchronous consumer or adapter, not direct synchronous dependency.

Suggested flow:

```text
Runtime operation
  -> builds RuntimeEvent / RuntimeMetric
  -> emits to configured ObservabilitySink
  -> sink stores, drops, or forwards asynchronously
  -> runtime continues regardless of sink result
```

## Privacy / Sensitive Data Rules

Observability records must be safe for local logs, CI artifacts, and future monitoring backends.

Allowed:

- Runtime names.
- Operation names.
- Status values.
- Durations.
- Counts.
- Stable low-cardinality classifications.
- Contract names and versions.
- Sanitized entity type.
- Sanitized error codes.

Restricted:

- Raw document text.
- OCR output.
- Extracted customer, supplier, product, invoice, price, or ERP values.
- Credentials, tokens, cookies, API keys, database URLs, and environment secrets.
- Full stack traces by default.
- Full file paths when they may include user-specific or sensitive information.

Rules:

- Prefer IDs and categories over values.
- Prefer counts over payload samples.
- Use allowlists for attributes.
- Sanitize error messages before emission.
- Treat observability files as potentially retained artifacts.

## Runtime Boundary Impact

Observability Improvements v1 is a cross-cutting hardening milestone. It must not weaken runtime boundaries.

Boundary rules:

- Runtime modules may depend on observability contracts and sink interfaces.
- Runtime modules must not synchronously call Monitoring Runtime.
- Monitoring Runtime must not become a required dependency for Workflow, Entity, Matching, Document, Review, or API Runtime execution.
- Observability contracts should live in a neutral package or module that does not import runtime internals.
- Runtime-specific instrumentation may adapt local runtime data into sanitized observability records.
- Observability must not mutate runtime contracts or persistence state except through explicit local sink configuration.

Expected boundary posture:

- Workflow Runtime owns orchestration context and trace propagation.
- Entity Runtime owns entity write observability.
- Matching Runtime owns decision observability.
- Monitoring Runtime, when implemented later, consumes emitted records asynchronously.

## Testing Strategy

Unit tests:

- Validate `RuntimeEvent`, `RuntimeMetric`, `RuntimeTraceContext`, and `RuntimeErrorRecord` construction.
- Validate required fields and allowed values.
- Validate privacy allowlist behavior.
- Validate metric dimension restrictions.
- Validate no-op sink behavior.
- Validate in-memory sink capture.
- Validate sink failure suppression.

Integration tests:

- Workflow run emits lifecycle events with stable correlation IDs.
- Workflow stage execution emits started/succeeded/failed events.
- Lock contention emits lock-related events and metrics.
- Entity write emits write, CAS conflict, idempotency, and escalation events where applicable.
- Matching decision emits decision and low-confidence metrics.

Regression tests:

- Existing workflow, entity, and matching tests pass with observability disabled.
- Runtime execution continues if sink emission raises an exception.
- Runtime boundary verification remains clean.

Privacy tests:

- Raw payload fields are not emitted.
- Error records are sanitized.
- Disallowed metric dimensions are rejected or dropped.

## Documentation Requirements

Required milestone documents:

- `docs/architecture/OBSERVABILITY_IMPROVEMENTS_V1_PLAN.md`
- `docs/architecture/OBSERVABILITY_IMPROVEMENTS_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/OBSERVABILITY_IMPROVEMENTS_V1_SUMMARY.md`
- `docs/architecture/OBSERVABILITY_IMPROVEMENTS_V1_HANDOFF.md`
- `docs/adr/ADR-011-observability-improvements.md`
- `docs/releases/v0.5-observability-improvements.md`

Required updates:

- `docs/ROADMAP.md`
- `TECHNICAL_DEBT.md`
- `docs/AGENT_CONTEXT.md` if current milestone or runtime status is stale.
- `CHANGELOG.md` if release notes are tracked there.

Documentation must explain:

- Event, metric, trace, and error contracts.
- Correlation propagation rules.
- Runtime boundary rules.
- Sink behavior.
- Privacy and sensitive data constraints.
- Testing and verification commands.
- Rollback or disablement guidance.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---:|---:|---|
| Observability introduces runtime coupling | Medium | High | Keep contracts neutral; forbid synchronous Monitoring Runtime calls. |
| Observability failures break runtime execution | Medium | High | Require fail-open sinks and regression tests. |
| Sensitive data leaks into logs | Medium | High | Use attribute allowlists and privacy tests. |
| Metric cardinality becomes unbounded | Medium | Medium | Restrict metric dimensions and reject raw IDs as dimensions. |
| Event names drift across runtimes | Medium | Medium | Maintain a central event name registry in docs and tests. |
| Correlation model is inconsistently propagated | Medium | Medium | Start propagation at Workflow Runtime and test common paths. |
| Too much scope delays v0.5 hardening | Medium | Medium | Limit v1 to passive observability, local sinks, and core runtime paths. |
| Future vendor integration requires rework | Low | Medium | Keep sink interface generic and vendor-neutral. |

## Effort Estimate

Estimated total: 8-12 person-days.

Breakdown:

- Architecture and ADR: 1-2 days.
- Contract design: 1 day.
- Sink design: 1 day.
- Workflow Runtime instrumentation: 2 days.
- Entity Runtime instrumentation: 2 days.
- Matching Runtime instrumentation: 1 day.
- Tests and boundary verification: 2-3 days.
- Documentation, release notes, summary, and handoff: 1-2 days.

Scope control:

- No dashboard.
- No external monitoring vendor.
- No alerting engine.
- No synchronous Monitoring Runtime.
- No runtime behavior changes beyond passive instrumentation.

## Release Plan

Phase 1: Architecture and Contracts

- Finalize this architecture plan.
- Create ADR-011 for passive runtime observability.
- Define event, metric, trace, and error contracts.
- Define privacy rules and metric dimension rules.

Phase 2: Sink Foundation

- Implement no-op, in-memory, and optional local JSONL sinks.
- Ensure sink failures are suppressed.
- Add contract and sink tests.

Phase 3: Workflow Runtime Instrumentation

- Add workflow run and stage lifecycle events.
- Add locking, lease, idempotency, and fallback metrics.
- Add trace context propagation through stage execution.

Phase 4: Entity and Matching Runtime Instrumentation

- Add entity write, CAS conflict, lock escalation, lease, and idempotency events.
- Add matching decision, strategy, low-confidence, and no-match events.
- Ensure no domain payload leakage.

Phase 5: Verification and Release

- Run unit, integration, regression, privacy, and boundary tests.
- Update roadmap and technical debt.
- Create implementation, summary, handoff, and release notes.
- Commit, push, and tag the milestone after implementation is complete.

Suggested milestone tag:

- `v0.5-observability-improvements`

## Definition of Done

Observability Improvements v1 is complete when:

- Architecture plan exists.
- Implementation plan exists.
- ADR-011 records the passive observability decision.
- Event, metric, trace, and error contracts are implemented and documented.
- Correlation model is implemented and documented.
- No-op and in-memory sinks exist.
- Optional local JSONL sink exists or is explicitly deferred.
- Sink behavior is fail-open.
- Workflow Runtime emits lifecycle, lock, lease, and idempotency observability records.
- Entity Runtime emits write, CAS conflict, escalation, lease, and idempotency observability records.
- Matching Runtime emits decision and confidence observability records if included in implementation scope.
- Observability can be disabled or left as no-op by default.
- Tests cover contract validation, sink behavior, correlation propagation, privacy rules, and runtime regression paths.
- Runtime Boundary Verification remains clean.
- No sensitive runtime payloads are emitted by default.
- `docs/ROADMAP.md` is updated.
- `TECHNICAL_DEBT.md` is updated.
- Summary, handoff, and release notes are created.
- Implementation is committed and pushed.
- Milestone tag is created after release verification.

End of document.
