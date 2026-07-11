# Review / Correction Runtime v1 Implementation Plan

**Milestone:** v0.7  
**Status:** Phases 1-5 complete and verified; release commit and tag pending
**Architecture:** `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_PLAN.md`

## 1. Milestone Overview

v0.7 hardens the existing `src/review_runtime` prototype into a deterministic backend runtime for review cases, field corrections, reviewer decisions, append-only audit history, and declarative reprocess requests. Each phase is sized for one Codex session and must stop after its own implementation, tests, boundary verification, and summary.

No phase adds UI, API, OCR, LLM behavior, external services, new dependencies, or a database. In-memory repositories are behavioral test implementations, not production persistence claims.

## 2. Cross-Phase Requirements

- Preserve runtime boundary rules and use public contracts or Workflow-owned adapters.
- Keep contracts immutable, versioned, JSON-compatible, and dependency-light.
- Use allowlisted enums, reason codes, metadata keys, and field-path syntax.
- Require idempotency keys and expected versions on state-changing commands.
- Keep corrected values in protected payloads, never generic metadata or observability.
- Do not mutate source Document, Entity, Matching, Transform, or Workflow artifacts.
- Preserve legacy review behavior only through explicit compatibility adapters and tests.
- Do not proceed automatically to the next phase.

## 3. Phase 1: Contracts and State Machine

### Objectives

- Define v1 enums and contracts for review cases, triggers, field references, corrections, decisions, audit events, and reprocess plan/request records.
- Implement the authoritative transition table and stable path-aware errors.
- Define privacy allowlists, collection/string bounds, field-path validation, and safe serialization.
- Map legacy `pending` to `review_required` and document legacy method compatibility.
- Reserve the `review` Workflow stage name without implementing it.

### Expected Files to Create

- `src/review_runtime/contracts/review_case.py`
- `src/review_runtime/contracts/correction.py`
- `src/review_runtime/contracts/decision.py`
- `src/review_runtime/contracts/audit_event.py`
- `src/review_runtime/contracts/reprocess.py`
- `src/review_runtime/contracts/enums.py`
- `src/review_runtime/state_machine.py`
- `src/review_runtime/errors.py`
- `src/review_runtime/privacy.py`
- `tests/review_runtime/__init__.py`
- `tests/review_runtime/test_contracts.py`
- `tests/review_runtime/test_state_machine.py`
- `tests/review_runtime/test_privacy.py`

### Expected Files to Modify

- `src/review_runtime/contracts/__init__.py`
- `src/review_runtime/__init__.py`
- `src/workflow_runtime/operations/stage_catalog.py`
- `tests/transforms/test_stage_catalog.py` or a focused workflow catalog test
- Existing review models only where needed for compatibility mapping; do not rewrite services yet.

### Tests

- JSON-compatible round trips and contract version rejection.
- Every allowed and forbidden lifecycle transition.
- All trigger types, decisions, statuses, and correction operations.
- Duplicate IDs, invalid paths, unbounded collections, unsafe metadata, and sensitive serialization rejection.
- Legacy `pending` mapping and reserved stage catalog behavior.
- Import-isolation checks for contract modules.

### Verification

```text
python -m pytest tests/review_runtime/test_contracts.py tests/review_runtime/test_state_machine.py tests/review_runtime/test_privacy.py -q
python -m pytest tests/boundaries -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after contracts, state machine, ADR alignment, focused tests, and verification. Do not implement repositories or services.

## 4. Phase 2: Review Case Service

### Objectives

- Define repository protocols for case projection, idempotency lookup, and compare-version update.
- Implement deterministic in-memory repository behavior.
- Implement idempotent case creation, retrieval, assignment/reassignment, safe listing/filtering, and state transitions that do not require a reviewer decision.
- Enforce expected case version, assignment ownership, deterministic ordering, and bounded page size.

### Expected Files to Create

- `src/review_runtime/contracts/repository.py` may be replaced or split into:
- `src/review_runtime/contracts/case_repository.py`
- `src/review_runtime/repositories/in_memory_case_repository.py`
- `src/review_runtime/services/case_service.py`
- `src/review_runtime/services/commands.py`
- `tests/review_runtime/test_case_repository.py`
- `tests/review_runtime/test_case_service.py`

### Expected Files to Modify

- `src/review_runtime/contracts/__init__.py`
- `src/review_runtime/repositories/__init__.py`
- `src/review_runtime/services/__init__.py`
- Existing `ReviewRepository` and `InMemoryReviewRepository` through deprecation-compatible adapters.

### Tests

- Every case trigger and required lineage field.
- Duplicate idempotency key returns the same case.
- Conflicting payload under one key fails deterministically.
- Assignment, reassignment audit intent, stale expected version, foreign reviewer, and resolved immutability.
- Deterministic list order, filters, pagination bounds, and repository copy/immutability behavior.
- Metadata and error privacy.

### Verification

```text
python -m pytest tests/review_runtime/test_case_repository.py tests/review_runtime/test_case_service.py -q
python -m pytest src/review_runtime/tests -q
python -m pytest tests/boundaries -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after case service behavior and compatibility verification. Do not implement correction, decision, audit persistence, or workflow integration.

## 5. Phase 3: Correction and Decision Service

### Objectives

- Implement field-level `replace` and `set_null` correction validation.
- Implement `approve`, `reject`, `correct`, `skip`, and `request_reprocess` decision handling.
- Add append-only audit repository/service with per-case sequence and payload fingerprints.
- Ensure case update and audit append have explicit unit-of-work semantics for a future durable repository.
- Adapt existing `ReviewService` and `FeedbackService` to the canonical services without maintaining a second state machine.

### Expected Files to Create

- `src/review_runtime/contracts/audit_repository.py`
- `src/review_runtime/repositories/in_memory_audit_repository.py`
- `src/review_runtime/services/correction_service.py`
- `src/review_runtime/services/decision_service.py`
- `src/review_runtime/audit/__init__.py`
- `src/review_runtime/audit/service.py`
- `src/review_runtime/audit/fingerprint.py`
- `tests/review_runtime/test_correction_service.py`
- `tests/review_runtime/test_decision_service.py`
- `tests/review_runtime/test_audit.py`

### Expected Files to Modify

- `src/review_runtime/services/review_service.py`
- `src/review_runtime/services/feedback_service.py`
- `src/review_runtime/models/status.py`
- Legacy model/repository modules only for explicit adapters.

### Tests

- Field-path and expected artifact-version checks.
- Protected corrected values and original-value fingerprints.
- All five decisions, required reasons/references, assignment ownership, idempotency, and conflicts.
- Append-only event sequence, prior/new state, lineage, deterministic fingerprint, and no update/delete surface.
- Atomic-failure simulation proving failed commands do not publish a successful projection.
- Legacy method parity for supported approve/reject/correct paths.
- Privacy assertions across dictionaries, JSON, exceptions, audit summaries, and metadata.

### Verification

```text
python -m pytest tests/review_runtime/test_correction_service.py tests/review_runtime/test_decision_service.py tests/review_runtime/test_audit.py -q
python -m pytest tests/review_runtime src/review_runtime/tests -q
python -m pytest tests/boundaries -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after correction, decision, audit, and compatibility verification. Do not implement reprocess or Workflow Runtime integration.

## 6. Phase 4: Reprocess Planning and Workflow Integration

**Completion note:** Completed as a safe dry-run planning boundary. Review Runtime creates and stores declarative plans and emits safe audit events. Workflow stage implementation, acknowledgement handling, observability registration, and execution were deferred to preserve runtime boundaries and the approved Phase 4 scope.

### Objectives

- Validate deterministic reprocess plans and create idempotent requests.
- Add acknowledgement handling without synchronous Review-to-Workflow calls.
- Implement the reserved Workflow `review` stage or adapter as a non-blocking case creator.
- Translate bounded validation/matching/document/entity outputs into neutral case requests using Workflow-owned adapters.
- Register fail-open review observability events and metrics with privacy-safe dimensions.

### Expected Files to Create

- `src/review_runtime/reprocess/__init__.py`
- `src/review_runtime/reprocess/planner.py`
- `src/review_runtime/reprocess/service.py`
- `src/workflow_runtime/operations/review_stage.py`
- `src/workflow_runtime/operations/review_artifact_adapter.py`
- `tests/review_runtime/test_reprocess.py`
- `tests/review_runtime/test_workflow_integration.py`

### Expected Files to Modify

- `src/review_runtime/services/__init__.py`
- `src/workflow_runtime/operations/__init__.py`
- `src/workflow_runtime/operations/stage_catalog.py`
- `src/observability/registry.py`
- Workflow Runtime tests for registration, validator alignment, and stage results.

### Integration Behavior

- `review` consumes an explicit review-trigger artifact/config, creates or resolves an idempotent case request, and returns a privacy-safe case reference.
- The stage never waits for a reviewer and never embeds full source rows.
- `request_reprocess` emits a declarative request. Workflow Runtime executes it in a separate invocation and returns an acknowledgement.
- Review Runtime records acknowledgement and transitions `reprocess_requested -> resolved`; it does not execute workflow stages itself.

### Tests

- Plans reject callbacks, expressions, URLs, credentials, unknown stages, unsafe parameters, and excessive attempts.
- Request idempotency, parent lineage, correction references, acknowledgement, and loop bounds.
- Trigger adapters for validation failure and matching ambiguity plus representative document/entity references.
- Workflow stage success/failure, catalog consistency, no synchronous wait, and safe metadata.
- Observability fail-open behavior and no corrected values/comments in events or metrics.
- Cross-runtime import isolation.

### Verification

```text
python -m pytest tests/review_runtime/test_reprocess.py tests/review_runtime/test_workflow_integration.py -q
python -m pytest tests/test_workflow_runtime.py tests/transforms tests/test_matching_runtime.py -q
python -m pytest tests/boundaries -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after reprocess planning, Workflow integration, observability, and focused verification. Do not begin release closure.

## 7. Phase 5: Verification, Docs, and Release Closure

**Completion note:** Completed with focused Review Runtime tests, boundary tests, the static boundary verifier, full regression, and release documentation. No production runtime feature was added in this phase.

### Objectives

- Add deterministic end-to-end review/correction/reprocess coverage.
- Verify privacy, lineage, legacy compatibility, stage catalog consistency, and all runtime boundaries.
- Produce summary, handoff, and release notes.
- Update roadmap, technical debt, changelog, architecture plan, implementation plan, and ADR accurately.
- Prepare but do not create the final tag.

### Expected Files to Create

- `tests/review_runtime/test_integration.py`
- `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_SUMMARY.md`
- `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_HANDOFF.md`
- `docs/releases/v0.7-review-correction-runtime.md`

### Expected Files to Modify

- `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_PLAN.md`
- `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_IMPLEMENTATION_PLAN.md`
- `docs/adr/ADR-013-review-correction-runtime.md`
- `docs/ROADMAP.md`
- `TECHNICAL_DEBT.md`
- `CHANGELOG.md`

### Integration Scenarios

- Validation failure -> case -> assignment -> correction -> approval -> resolution.
- Matching ambiguity -> case -> reject or skip -> resolution.
- Corrected case -> reprocess request -> Workflow acknowledgement -> resolution.
- Duplicate command replay and stale version conflict.
- Legacy review service compatibility.
- Metadata, audit, observability, and exception privacy.

### Verification

```text
python -m pytest tests/review_runtime src/review_runtime/tests -q
python -m pytest tests/test_workflow_runtime.py tests/transforms tests/test_matching_runtime.py -q
python -m pytest tests/boundaries -q
python scripts/verify_boundaries.py
python -m pytest -q
git diff --check
git status --short --branch
```

Full-suite failures must be reported exactly and classified only with evidence. Release notes must not claim durable persistence, transactional database behavior, authenticated reviewers, or production UI/API readiness.

### Stop Condition

Stop after verification and release documentation. Do not commit, push, or tag unless separately instructed.

## 8. Backward Compatibility

- Map legacy `ReviewStatus.PENDING` to `review_required` at compatibility boundaries.
- Preserve supported `ReviewService` method signatures through adapters where doing so does not bypass v1 validation.
- Keep legacy serialized fields readable during v0.7; write canonical v1 contracts for new operations.
- Remove confidence-based automatic approval from canonical case creation. Legacy behavior may remain only behind an explicitly named compatibility adapter and must not affect v1 cases.
- Do not silently reinterpret unrestricted legacy metadata as safe v1 metadata; validate or reject it.

## 9. Boundary Requirements

- Review contracts and state machine import only standard library and review-owned neutral helpers.
- Review Runtime does not import Document Engine, Entity Runtime, Matching Runtime, Transform, API, UI, Streamlit, or FlowSync internals.
- Document, Entity, Matching, and Transforms do not import Review Runtime.
- Workflow Runtime may depend on Review Runtime public contracts/services through explicit adapters.
- Observability remains passive and fail-open.
- Repository implementations do not leak storage details into contracts or services.

## 10. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Prototype and v1 behavior diverge | Canonical services plus tested compatibility adapters; no parallel transition logic. |
| In-memory tests overstate durability | State clearly that persistence and atomic database implementation are deferred. |
| Concurrent reviewers overwrite state | Expected versions, idempotency keys, assignment checks, and conflict tests. |
| Sensitive correction content leaks | Protected payload separation, allowlists, sanitization, and serialization tests. |
| Reprocess creates loops or duplicate runs | Parent lineage, request idempotency, attempt limits, and Workflow-owned execution policy. |
| Workflow coupling violates boundaries | Translation lives in Workflow adapters; Review emits neutral requests only. |

## 11. Definition of Done

- Phases 1-5 are implemented and individually verified.
- Required triggers, statuses, decisions, corrections, audit events, and reprocess contracts are supported.
- State transitions, assignment, idempotency, and expected-version conflicts are deterministic.
- Audit history is append-only and lineage-aware.
- Corrected values are absent from unsafe metadata, errors, logs, metrics, and audit summaries.
- Reprocess planning is non-blocking and dry-run only; future execution remains Workflow-owned.
- Existing review compatibility and runtime boundaries pass.
- Full regression passes in the provisioned project environment.
- Release documentation is complete and the recommended tag is documented, not created.

## 12. Commit and Tag Strategy

One commit per completed phase is recommended:

1. `feat: add review runtime contracts and state machine`
2. `feat: add deterministic review case service`
3. `feat: add review corrections decisions and audit`
4. `feat: integrate review reprocess workflow planning`
5. `chore: close v0.7 review correction runtime`

Recommended final tag after Phase 5 verification:

`v0.7-review-correction-runtime`
