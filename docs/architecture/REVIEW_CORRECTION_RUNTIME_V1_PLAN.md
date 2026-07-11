# Review / Correction Runtime v1 Architecture Plan

**Milestone:** v0.7  
**Status:** Implemented and verified; release commit and tag pending
**Scope:** Deterministic backend review, field correction, decision, audit, lineage, and reprocess-request contracts

## 1. Problem Statement

The platform can deterministically ingest, extract, validate, transform, match, and orchestrate data, but exceptions do not yet have a complete backend lifecycle. Validation failures, uncertain extraction, ambiguous matches, possible duplicates, blocked customers, invalid data, export failures, and manual escalations need one authoritative path for human review and correction.

`src/review_runtime` already contains a prototype `ReviewItem`, in-memory repositories, threshold routing, decisions, corrections, and feedback capture. That foundation is useful but incomplete: its states and decisions do not cover the required lifecycle, corrections are not field-addressed or version-aware, metadata can contain unrestricted values, audit records are replaceable rather than append-only, and reprocessing has no declarative contract. v0.7 hardens this existing runtime rather than creating a parallel implementation.

## 2. Business Purpose

v0.7 provides a backend source of truth for operational exception handling. It must let an authorized reviewer understand why a case exists, claim it, record a bounded decision, correct specific fields, and request deterministic reprocessing while preserving the original artifact and complete decision history.

The runtime enables later Streamlit and FlowSync consumers without assigning either client ownership of state transitions, correction validation, audit rules, or reprocess policy.

## 3. Goals

1. Define versioned JSON-compatible review, correction, decision, audit, and reprocess contracts.
2. Support cases created for `validation_failure`, `extraction_uncertainty`, `matching_ambiguity`, `duplicate_detection`, `blocked_customer`, `invalid_data`, `export_error`, and `manual_escalation`.
3. Enforce one deterministic review lifecycle and explicit transition table.
4. Support reviewer decisions `approve`, `reject`, `correct`, `skip`, and `request_reprocess`.
5. Support field-level corrections against versioned source artifacts without mutating historical artifacts.
6. Maintain append-only, correlation-aware audit and lineage records.
7. Produce declarative reprocess requests that Workflow Runtime may consume asynchronously.
8. Keep runtime metadata and observability records privacy-safe and bounded.
9. Preserve current runtime boundaries and provide an explicit migration path for the existing prototype.

## 4. Non-Goals

- Streamlit, FlowSync, or any other UI implementation.
- Public or internal API implementation.
- Database schemas, migrations, or a production persistence backend.
- OCR, LLM review, LLM correction, automated reviewer decisions, or model training.
- Direct mutation of Document, Entity, Matching, Transform, or Workflow Runtime stores.
- Synchronous waiting for a human inside a workflow execution.
- Authentication, authorization-provider integration, reviewer workforce management, or notifications.
- Bulk correction, collaborative editing, SLA scheduling, or queue optimization.
- A general rules language or executable correction expressions.

## 5. Current State

The existing runtime provides:

- `ReviewRequest`, `ReviewItem`, `ReviewDecision`, `ReviewCorrection`, and `FeedbackRecord` dataclasses.
- `pending`, `in_review`, `approved`, `rejected`, and `corrected` statuses.
- In-memory review and feedback repositories.
- Basic create, assign, approve, reject, correct, and feedback services.
- Confidence-threshold routing and optional automatic approval.

The v0.7 design changes the default posture. A case explicitly raised for human review is never silently auto-approved by Review Runtime. Upstream deterministic policy decides whether to create a case. Once created, the case begins in `review_required`, and only the state machine may change it.

Compatibility work must map legacy `pending` to `review_required` and preserve existing public methods through narrow adapters where practical. Existing classes must not become a second source of truth.

## 6. Proposed Architecture

The runtime has five layers:

1. **Contracts** define immutable, versioned, JSON-compatible records and enums.
2. **State machine** validates transitions and decision preconditions without I/O.
3. **Case service** creates, retrieves, assigns, lists, and transitions cases through repository protocols.
4. **Correction and decision services** validate field corrections, append decisions, and produce audit events.
5. **Reprocess planner** converts an accepted request into a declarative `ReprocessRequest` for Workflow Runtime.

Repositories remain protocol boundaries. v0.7 uses deterministic in-memory implementations for tests and local execution. Durable storage, transactions, indexes, and migrations are deferred; contract and service semantics must not depend on a specific database.

All externally supplied IDs and timestamps are validated. Services accept an injectable clock and ID factory for deterministic tests. Commands carry an `idempotency_key` and `expected_case_version`; duplicate commands return the existing result, while stale versions fail with a stable conflict error.

## 7. Runtime Boundaries

- **Review Runtime owns:** review cases, lifecycle transitions, reviewer decisions, correction records, audit events, and reprocess intent.
- **Workflow Runtime owns:** orchestration, conversion of upstream outputs into review-case requests, stage registration, pausing/continuing workflow policy, and execution of reprocess requests.
- **Document Engine owns:** document artifacts, parsing, extraction structure, and document lineage. Review Runtime stores references only and never parses documents.
- **Entity Runtime owns:** entity artifacts, entity versions, validation, and persistence. Review Runtime never writes entity stores directly.
- **Matching Runtime owns:** candidates, confidence, ambiguity, duplicate signals, and match decisions. It does not import Review Runtime or mutate review cases.
- **Transforms validation owns:** deterministic validation evaluation. Workflow adapters translate bounded validation results into review triggers.
- **Observability owns:** passive event/metric transport. Review emission is fail-open and never controls review success.

Because existing boundary rules prohibit Document and Entity runtimes from importing Review Runtime, upstream runtimes emit their own public artifacts. Workflow Runtime performs the translation to neutral review contracts. `src/review_runtime` must not import Document Engine, Entity Runtime, Matching Runtime, Transform, UI, API, FlowSync, or Streamlit internals.

## 8. Review Lifecycle State Machine

Required states:

- `review_required`: case exists and is unassigned.
- `in_review`: an identified reviewer has claimed the case.
- `corrected`: one or more validated corrections have been recorded.
- `approved`: reviewer accepted the referenced artifact or corrected result.
- `rejected`: reviewer rejected the referenced artifact or proposed outcome.
- `skipped`: reviewer intentionally deferred or declined the case with a reason.
- `reprocess_requested`: reviewer requested a new deterministic processing attempt.
- `resolved`: downstream handling is acknowledged and the case is closed.

Allowed transitions:

| From | To | Command / Condition |
|---|---|---|
| `review_required` | `in_review` | assign/claim by reviewer |
| `review_required` | `skipped` | authorized `skip` with reason |
| `in_review` | `corrected` | `correct` with at least one valid correction |
| `in_review` | `approved` | `approve` |
| `in_review` | `rejected` | `reject` |
| `in_review` | `skipped` | `skip` with reason |
| `in_review` | `reprocess_requested` | `request_reprocess` with valid plan |
| `corrected` | `approved` | approve corrected result |
| `corrected` | `in_review` | continue review with same assigned reviewer |
| `corrected` | `reprocess_requested` | reprocess using accepted corrections |
| `approved` | `resolved` | downstream acknowledgement or no further action |
| `rejected` | `resolved` | downstream acknowledgement |
| `skipped` | `resolved` | closure acknowledgement |
| `reprocess_requested` | `resolved` | Workflow Runtime accepts or rejects request |

All other transitions fail with a stable path-aware error. A resolved case is immutable. Reprocessing creates a new linked processing attempt and, if another review is needed, a new case linked by `parent_case_id`; it does not reopen or rewrite the original case.

## 9. Review Case Contract

`ReviewCase` is immutable and carries `contract_version: 1` plus:

- Identity: `case_id`, `case_version`, optional `parent_case_id`.
- Trigger: `case_type`, stable `reason_codes`, priority, and safe summary.
- Lifecycle: status, assigned reviewer ID, created/updated timestamps.
- Lineage: `source_runtime`, `source_artifact_type`, `source_artifact_id`, `source_artifact_version`, optional workflow/run/stage and correlation IDs.
- Scope: ordered field references and bounded issue references; no complete source row.
- Context: allowlisted, JSON-compatible safe attributes only.
- Concurrency: creation idempotency key and current version.

Case creation validates required lineage, enum values, bounded collection sizes, safe context keys, and duplicate field references before persistence. The deduplication key is caller-provided and scoped to source artifact version plus trigger policy; Review Runtime does not infer identity from sensitive values.

## 10. Correction Contract

`FieldCorrection` contains:

- `correction_id`, `case_id`, and `contract_version`.
- Target artifact type, ID, expected version, and canonical field path.
- Operation: `replace` or `set_null` in v1.
- Corrected JSON-compatible value in a protected payload field.
- Original-value fingerprint, not the raw original value.
- Reason code, optional bounded note, reviewer ID, timestamp, and idempotency key.
- Correlation and lineage references.

Corrections are proposals owned by Review Runtime. Applying them to a domain artifact is a separate deterministic adapter owned by that domain or Workflow Runtime. Application must use optimistic version checks and produce a new artifact/version. Corrections never overwrite the source artifact or prior correction.

Corrected values may be sensitive and are therefore allowed only in the protected correction payload. They must never be copied into generic metadata, logs, metrics, exception text, audit summaries, or reprocess metadata.

## 11. Reviewer Decision Contract

`ReviewerDecision` contains decision ID, case ID/version, decision type, reviewer ID, timestamp, reason code, bounded comment, correction IDs, optional reprocess-plan ID, idempotency key, and correlation context.

Preconditions:

- `approve` and `reject` require `in_review` or the documented corrected path.
- `correct` requires at least one correction owned by the case.
- `skip` requires a reason code.
- `request_reprocess` requires a validated reprocess plan.
- A reviewer cannot decide a case assigned to another reviewer unless an explicit reassignment event has occurred.

Decision records are append-only. The case stores the current state and references to decision/correction IDs, not mutable embedded histories.

## 12. Audit and Lineage Model

Every accepted command appends one or more `ReviewAuditEvent` records with:

- `event_id`, case ID/version, monotonically increasing sequence, event type, prior/new state.
- Actor type and actor ID, UTC timestamp, idempotency key, and correlation IDs.
- Source artifact and workflow lineage references.
- Decision/correction/reprocess IDs and safe reason codes.
- Payload fingerprint for tamper/reconciliation checks.

Events are append-only and ordered per case. Repository protocols expose append and ordered read operations; update/delete of prior events is not part of the contract. In-memory persistence provides behavioral verification only. Database transactions and cryptographic signing remain deferred, but the service sequence must be designed so a durable implementation can atomically compare case version, append events, and store the new case projection.

## 13. Reprocess / Retry Model

Review Runtime creates intent; Workflow Runtime executes it.

`ReprocessPlan` declares the source artifact reference, requested start stage or named workflow, correction IDs to apply, allowed reason code, maximum attempt count, and safe parameters. It contains no executable callback, Python expression, URL, credentials, or raw source row.

`ReprocessRequest` adds request ID, case ID/version, parent workflow/run correlation, idempotency key, and status `requested`. Workflow Runtime may accept or reject it and returns a separate acknowledgement. Review Runtime records that acknowledgement and resolves the case. Execution failure does not rewrite the decision; subsequent escalation creates a linked case or retry request according to Workflow policy.

No review service synchronously invokes Workflow Runtime, and no human wait holds a workflow lock or lease.

## 14. Integration Points

| Producer / Consumer | Integration |
|---|---|
| Document Engine | Workflow adapter creates `extraction_uncertainty`, `invalid_data`, or manual cases from public document references and bounded issue summaries. |
| Entity Runtime | Workflow adapter creates validation, blocked-customer, or duplicate cases using entity IDs/versions and field references. Corrections return as proposals for version-checked application. |
| Matching Runtime | Workflow adapter creates ambiguity/duplicate cases from match result IDs, candidate counts, confidence buckets, and explanation codes, not complete candidates. |
| Workflow Runtime | Owns a reserved then implemented `review` stage, case-request adaptation, non-blocking review-required result, and asynchronous reprocess execution/acknowledgement. |
| Transforms validation | Bounded validation issues map to review field references and reason codes; full rows and raw failed values are excluded. |
| Observability | Fail-open events and low-cardinality metrics cover case creation, transitions, decisions, corrections, conflicts, and reprocess requests. |

## 15. Streamlit Consumption Later

Streamlit may consume case summaries, safe issue summaries, protected field values through an authorized backend interface, allowed decisions, transition results, and audit timelines. It may submit commands carrying expected case version and idempotency key.

Streamlit must not implement transition rules, mutate repositories, apply corrections, infer reviewer decisions, construct audit events, or own reprocess execution.

## 16. FlowSync Consumption Later

FlowSync may consume queue counts, case status, assignment summaries, decision outcomes, safe audit events, reprocess acknowledgements, and passive metrics. It may submit commands only through a future backend interface.

FlowSync must not become the system of record, store authoritative correction history, bypass version checks, or make review decisions.

## 17. Security and Privacy Requirements

- Deny unknown metadata keys; allow only documented scalar safe attributes.
- Never include full document text, complete rows, candidate records, credentials, tokens, or raw sensitive values in generic metadata.
- Bound comments, reason lists, field references, issue references, and audit query results.
- Separate protected correction payloads from safe summaries and observability attributes.
- Sanitize exception messages and reject control characters or unsafe field paths.
- Use stable actor IDs; authentication and role verification are future boundary concerns, not trusted metadata strings.
- Require idempotency keys and expected versions for state-changing commands.
- Record every assignment, reassignment, decision, correction, conflict, and reprocess acknowledgement.
- Do not emit corrected values or reviewer comments to observability sinks.

## 18. Testing Strategy

- Contract round-trip and JSON-compatibility tests for all v1 records.
- Exhaustive state-transition table tests, including resolved immutability.
- Case creation tests for every trigger type, idempotency, deterministic ordering, and bounded context.
- Correction tests for field paths, version checks, fingerprints, protected values, and duplicate commands.
- Decision tests for all five decisions and their preconditions.
- Append-only audit ordering, sequence, lineage, and immutability tests.
- Reprocess plan/request validation and Workflow adapter tests without executing external services.
- Privacy tests proving raw rows/values never enter metadata, errors, audit summaries, or observability.
- Boundary tests proving upstream runtimes and shared transforms do not import Review Runtime, and Review Runtime does not import upstream internals.
- Backward-compatibility tests for the documented legacy status/method adapters.
- End-to-end deterministic test from validation/matching trigger through correction, approval or reprocess request, acknowledgement, and resolution.

No test requires network access, a browser, OCR, LLMs, external services, UI, API, or a database.

## 19. Implementation Phases

1. **Contracts and state machine:** v1 contracts, enums, errors, privacy rules, transition table, compatibility mapping, ADR, and boundary tests.
2. **Review case service:** idempotent creation, assignment, listing/filtering, expected-version transitions, repository protocols, and in-memory repository.
3. **Correction and decision service:** field corrections, five decisions, append-only audit service, lineage, privacy enforcement, and legacy service adapters.
4. **Reprocess planning and workflow integration:** declarative plans/requests, Workflow-owned review adapter/stage, acknowledgement flow, and fail-open observability.
5. **Verification and release closure:** integration/privacy/boundary regression, summary/handoff/release notes, roadmap/debt/changelog closure, and tag instructions.

All five phases are complete. Phase 4 intentionally stopped at dependency-free dry-run reprocess planning. Workflow review-stage adapters, acknowledgements, observability registration, and workflow execution remain deferred and are not release claims for v0.7.

## 20. Risks and Deferred Work

| Risk | Mitigation / Deferred Work |
|---|---|
| Existing prototype contracts conflict with v1 semantics | Add explicit compatibility mappings and one canonical service path; do not maintain parallel state machines. |
| Lost updates during concurrent review | Require expected case version and idempotency keys; durable atomic compare-and-append is deferred with database work. |
| Sensitive values leak through comments or metadata | Separate protected payloads, allowlist metadata, bound strings, and add serialization/privacy tests. |
| Correction cannot be applied to a changed artifact | Carry expected artifact version and fail deterministically; create a new case for reconciliation. |
| Workflow waits indefinitely for a human | Return a non-blocking review-required result; re-entry is a separate invocation. |
| Audit projection and event append diverge in memory | Define repository unit-of-work semantics now; production transaction implementation is deferred. |
| Reviewer identity is spoofable without auth | Treat actor ID as supplied execution context; authentication/authorization integration is deferred. |
| Reprocess loops | Require attempt count, parent lineage, idempotency, and workflow-owned maximums. |

Deferred capabilities include production persistence, API/UI, notifications, access-control integration, queue SLAs, bulk review, correction application for every domain type, cryptographic audit signing, learning pipelines, and automated decisions.

## 21. Definition of Done

v0.7 is complete when:

- All required contracts serialize to plain JSON-compatible dictionaries and reject invalid/unsafe input.
- Every lifecycle transition and reviewer decision is deterministic and exhaustively tested.
- Case creation supports all required trigger types and is idempotent.
- Field corrections are version-aware, lineage-linked, immutable, and absent from unsafe metadata.
- Audit events are append-only and ordered per case.
- Reprocess requests are declarative, bounded, and consumed asynchronously through Workflow-owned integration.
- Existing runtime boundaries remain compliant and the legacy prototype has one documented compatibility path.
- Streamlit and FlowSync remain consumers only; no UI, API, database, OCR, LLM, or external dependency is introduced.
- Focused, boundary, and full regression suites pass and release documentation accurately states remaining limitations.
