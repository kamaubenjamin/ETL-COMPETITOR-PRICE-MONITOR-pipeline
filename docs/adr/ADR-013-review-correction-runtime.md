# ADR-013: Review / Correction Runtime v1

## Status

Accepted and implemented for v0.7; release commit and tag pending.

## Context

The platform produces deterministic document, entity, validation, transformation, matching, and workflow artifacts, but operational exceptions need a complete human-review lifecycle. The repository already contains a Review Runtime prototype with basic items, statuses, decisions, corrections, feedback, and in-memory repositories. It does not yet provide the required lifecycle, field-addressed version-aware corrections, append-only audit history, privacy-safe metadata, or declarative reprocessing.

Review cases may originate from validation failures, extraction uncertainty, matching ambiguity, duplicate detection, blocked customers, invalid data, export errors, or manual escalation. Streamlit and FlowSync may present this information later, but neither may own review rules or authoritative state.

## Decision

We will harden `src/review_runtime` as the backend source of truth for v0.7 using immutable versioned contracts, a deterministic state machine, repository protocols, append-only audit events, and declarative reprocess requests.

The canonical lifecycle is:

`review_required`, `in_review`, `corrected`, `approved`, `rejected`, `skipped`, `reprocess_requested`, and `resolved`.

The canonical reviewer decisions are:

`approve`, `reject`, `correct`, `skip`, and `request_reprocess`.

Case creation is idempotent. State-changing commands require an expected case version and idempotency key. A resolved case is immutable. Reprocessing does not reopen a case; it creates a linked processing attempt and any later exception creates a linked child case.

Field corrections reference a source artifact ID/version and canonical field path. They preserve an original-value fingerprint and a protected corrected value. They are immutable proposals; Review Runtime does not directly mutate Document, Entity, Matching, Transform, or Workflow artifacts.

Every accepted command produces ordered append-only audit events with actor, state transition, reason, correlation, and artifact lineage. Generic metadata, errors, logs, metrics, and audit summaries must not contain full source rows or raw sensitive values.

Review Runtime emits a bounded declarative `ReprocessRequest` and can convert it into a dry-run `ReprocessPlan`. It does not execute workflows, call WorkflowRunner, or hold workflow execution open for a human. Workflow execution and acknowledgement remain future Workflow Runtime responsibilities.

## Runtime Boundary Decision

- Upstream runtimes publish their own public artifacts and do not import Review Runtime.
- Workflow Runtime owns adapters that translate public validation, document, entity, and matching outputs into review-case requests.
- Review Runtime does not import upstream runtime internals.
- Observability is passive and fail-open.
- Streamlit and FlowSync are future consumers only.

This refines ADR-008 rather than replacing its runtime ownership decision. ADR-008 established Review Feedback Runtime as a distinct boundary; ADR-013 defines the v0.7 contracts, lifecycle, privacy model, and integration mechanics.

## Persistence Decision

v0.7 defines repository and unit-of-work semantics and supplies deterministic in-memory implementations. It does not select or implement a production database. Durable atomic compare-and-append, indexes, retention, migrations, and cryptographic audit signing are deferred.

## Consequences

### Benefits

- One backend authority for review transitions and corrections.
- Explainable, deterministic human decisions with complete lineage.
- Safe integration with existing runtimes without reverse dependencies.
- UI and control-plane consumers can evolve without duplicating business logic.
- Contracts are ready for later durable persistence and API exposure.

### Tradeoffs

- In-memory v1 behavior does not provide production durability or multi-process coordination.
- Optimistic versioning adds conflict handling for clients and future adapters.
- Protected correction values require careful separation from metadata and telemetry.
- Non-blocking human review requires a separate workflow resumption/reprocess invocation.

## Rejected Alternatives

### Put review logic in Streamlit or FlowSync

Rejected because clients would become inconsistent sources of truth and could bypass audit, privacy, and transition rules.

### Let upstream runtimes create and mutate review records directly

Rejected because it creates reverse dependencies and spreads review semantics across Document, Entity, Matching, and Transform runtimes.

### Mutate source artifacts in place

Rejected because it destroys lineage and makes correction history irreproducible. Corrections must create version-checked downstream artifacts.

### Keep workflows blocked until a reviewer responds

Rejected because human latency is incompatible with workflow locks, leases, and deterministic execution duration.

### Use LLMs to decide or correct cases

Rejected for v1 because decisions must remain human-authored, deterministic, explainable, and locally testable.

## Security and Privacy Consequences

- Corrected values are protected payload fields, not generic metadata.
- Unknown metadata keys and unsafe field paths are rejected.
- Comments and collections are bounded and sanitized.
- Actor authentication remains a future interface concern, but every command records the supplied actor context.
- Observability contains low-cardinality state/reason information only.

## Follow-Up

The five phases are implemented and verified. Closure evidence is recorded in `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_SUMMARY.md`, the future-agent guidance is in `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_HANDOFF.md`, and release instructions are in `docs/releases/v0.7-review-correction-runtime.md`. Durable persistence, trusted identity, Workflow execution/acknowledgement, UI, and API remain follow-up work.
