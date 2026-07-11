# Review / Correction Runtime v1 Summary

**Milestone:** v0.7
**Status:** Implemented and verified; commit and tag pending

## Milestone Purpose

v0.7 establishes Review Runtime as the deterministic backend authority for human review cases, field-level corrections, reviewer decisions, audit history, and dry-run reprocess planning. It provides no UI, API, database, OCR, LLM decision-making, or workflow execution.

## Delivered Capabilities

- Immutable, JSON-compatible review, correction, decision, audit, reprocess-request, and reprocess-plan contracts.
- Explicit lifecycle state machine with optimistic case versions and deterministic transition errors.
- In-memory repository protocols and implementations with defensive copies, idempotent creation, ordered reads, and atomic case/audit updates.
- Review case creation, assignment, filtering, transition, correction, decision, resolution, and audit services.
- Field-level `replace` and `set_null` corrections with controlled values, source lineage, reason codes, and privacy-safe errors.
- Decisions for `approve`, `reject`, `correct`, `skip`, and `request_reprocess`.
- Append-only, ordered audit events for accepted commands.
- Declarative dry-run reprocess plans with deterministic artifact references and safe stage validation.

## Phase Summary

1. **Contracts and state machine:** Added canonical contracts, enums, errors, privacy validation, legacy `pending` normalization, and the explicit transition table.
2. **Review case service:** Added repository boundaries, deterministic in-memory storage, idempotent creation, assignment, listing, optimistic version checks, and case audit events.
3. **Correction and decision service:** Added controlled field corrections, all five decisions, request intent, atomic repository writes, append-only audit history, and privacy enforcement.
4. **Reprocess planning:** Added dry-run plans, local safe stage validation, deterministic artifact invalidation/retention lists, in-memory plan storage, and `reprocess_plan_created` audit events.
5. **Verification and closure:** Verified focused Review Runtime tests, runtime boundaries, and the complete repository regression suite; added release and handoff documentation.

## Final Review Runtime Modules

- `src/review_runtime/contracts/`: canonical records, enums, validation helpers, audit, correction, decision, case, and request contracts.
- `src/review_runtime/state_machine.py`: lifecycle transition and decision mapping rules.
- `src/review_runtime/repositories/`: repository protocol and deterministic in-memory implementation.
- `src/review_runtime/services/`: case, correction/decision, and reprocess planning services.
- `src/review_runtime/reprocess/`: dependency-free dry-run plan contract and planner.
- `src/review_runtime/privacy.py`: bounded metadata allowlists and sanitization.

## Lifecycle States

`review_required`, `in_review`, `corrected`, `approved`, `rejected`, `skipped`, `reprocess_requested`, and `resolved`. `resolved` is terminal.

## Supported Decisions

`approve`, `reject`, `correct`, `skip`, and `request_reprocess`, subject to state, assignment, correction-reference, reason, and expected-version preconditions.

## Correction Behavior

Corrections target explicit field paths and source artifact lineage. They are immutable proposals and never mutate source artifacts. Controlled corrected values are permitted only in correction payloads and are excluded from generic metadata, errors, and audit summaries.

## Audit Behavior

Accepted commands append ordered audit events with actor, status, reason, sequence, and safe lineage metadata. Failed validation, invalid transitions, stale versions, and failed reprocess planning append nothing. The in-memory repository models atomic compare-and-write behavior but is not durable storage.

## Reprocess Planning Behavior

Review Runtime converts an existing declarative request into a `dry_run=True` plan. Plans contain stage names and artifact identifiers only, are stored deterministically in memory, and do not execute workflows or mutate artifacts. Workflow Runtime remains the future execution owner.

## Runtime Boundaries

Review Runtime does not import Document Engine, Entity Runtime, Matching Runtime, Transforms, API, UI, Streamlit, FlowSync, or WorkflowRunner internals. Phase 4 uses a dependency-free local safe-stage allowlist because the current boundary policy does not expose a neutral shared stage contract.

## Verification Results

- `python -m pytest tests/review_runtime -q`: 175 passed.
- `python -m pytest tests/review_runtime tests/boundaries -q`: 197 passed.
- `python scripts/verify_boundaries.py`: compliant, with two pre-existing BOM scan warnings.
- `python -m pytest -q`: 852 passed, 711 warnings.
- `git diff --check`: passed before closure documentation; rerun at release handoff.

## Backward Compatibility

Legacy `pending` input maps to canonical `review_required`. Existing prototype modules remain present, while new operations use the canonical v1 contracts and services. No existing runtime public contract was intentionally removed.

## Deferred Work

- Durable database persistence, transactions, migrations, retention, and multi-process coordination.
- Authentication, authorization, reviewer roles, assignment policy, and protected-value access control.
- Workflow review-stage adapters, reprocess acknowledgement, and actual reprocess execution.
- Shared public stage catalog to replace the local reprocess allowlist.
- API, Streamlit, FlowSync, notifications, queues, dashboards, and observability instrumentation.
- OCR, LLM decisions/corrections, bulk review, and full correction application to domain artifacts.
