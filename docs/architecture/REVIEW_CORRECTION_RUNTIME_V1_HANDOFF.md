# Review / Correction Runtime v1 Handoff

**Milestone:** v0.7
**State:** Implemented and verified; release commit and tag pending

## Current State

Review Runtime now provides deterministic contracts, lifecycle enforcement, in-memory case storage, field corrections, reviewer decisions, append-only audit history, and dry-run reprocess planning. It is a backend runtime foundation, not a deployed human-review product.

## Important Files

- `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_PLAN.md`
- `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_IMPLEMENTATION_PLAN.md`
- `docs/adr/ADR-013-review-correction-runtime.md`
- `src/review_runtime/contracts/`
- `src/review_runtime/state_machine.py`
- `src/review_runtime/privacy.py`
- `src/review_runtime/repositories/`
- `src/review_runtime/services/`
- `src/review_runtime/reprocess/`
- `tests/review_runtime/`
- `tests/boundaries/`

## Test Commands

```text
python -m pytest tests/review_runtime -q
python -m pytest tests/review_runtime tests/boundaries -q
python scripts/verify_boundaries.py
python -m pytest -q
git diff --check
git status --short --branch
```

## Extension Rules

- Add behavior through canonical contracts and services, not the legacy prototype state model.
- Keep commands deterministic, injectable for IDs/timestamps, and protected by expected versions where state changes.
- Preserve immutable source artifacts and store references rather than raw rows or documents.
- Make durable repositories honor the existing atomic case/audit semantics and defensive-copy behavior.
- Keep workflow execution outside Review Runtime. Translate plans through a public, neutral integration adapter.
- Add focused privacy, failure-atomicity, idempotency, and boundary tests with every extension.

## What Not To Change

- Do not add alternate lifecycle states or decision paths without updating ADR-013 and exhaustive transition tests.
- Do not bypass the state machine or repository unit-of-work methods.
- Do not make Streamlit, FlowSync, API handlers, or Workflow Runtime the owner of review state.
- Do not mutate source artifacts when recording corrections.
- Do not place corrected values, raw rows, document content, credentials, comments, or arbitrary payloads in metadata or audit summaries.
- Do not turn reprocess planning into synchronous workflow execution.

## Privacy And Security Rules

Metadata is allowlisted, scalar, and bounded. Errors identify paths and stable codes without echoing submitted values. Corrected values remain controlled correction payloads. Actor IDs are recorded but are not authenticated by v0.7; future interfaces must supply trusted identity and authorization context.

## Known Risks And Deviations

- Persistence is process-local and non-durable.
- Actor identity is caller supplied; authentication and authorization are absent.
- The safe reprocess stage list is locally mirrored and may drift from Workflow Runtime.
- Phase 4 stops at dry-run planning. No review stage, workflow acknowledgement, observability registration, or reprocess execution was delivered.
- Boundary verification skips two pre-existing files with U+FEFF BOM parsing warnings.

## Next Recommended Milestone

Define a durable Review Runtime persistence and trusted service boundary before building UI consumers. That milestone should cover database-backed atomic case/audit writes, authentication/authorization context, protected correction-value access, and a neutral asynchronous Workflow Runtime acknowledgement contract.
