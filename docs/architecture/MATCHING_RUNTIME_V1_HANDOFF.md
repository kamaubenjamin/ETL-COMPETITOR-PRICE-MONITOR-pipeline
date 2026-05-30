# Matching Runtime V1 Handoff

## Current Status

Matching Runtime v1 is implemented and integrated into the workflow runtime. It is ready for review, onboarding, and the next phased work item: durable storage and review integration.

## Ownership Notes

- `src/matching_runtime/services/matching_service.py` is the primary orchestration entrypoint.
- `src/workflow_runtime/operations/matching_stage.py` is the workflow integration point.
- Match contracts are defined under `src/matching_runtime/contracts` and models under `src/matching_runtime/models`.

## Open Considerations

- Review how confidence calculators behave for partial fuzzy matches and whether field weights should be tuned.
- Decide whether historical match evidence should be persisted to disk or external storage.
- Confirm if `MatchType.MANUAL` should be surfaced as a low-confidence/exception outcome in v1.

## Recommended Next Work

1. Implement durable `HistoricalMatchStore` persistence.
2. Add a `ReviewStage` that can accept low-confidence match results and route them for manual validation.
3. Expose match metadata in the workflow UI or alerting layer for traceability.
4. Extend master data repository adapters to support external ERP/CRM sources.

## Handoff Checklist

- [x] `docs/architecture/MATCHING_RUNTIME_V1_ARCHITECTURE.md` exists
- [x] `docs/architecture/MATCHING_RUNTIME_V1_IMPLEMENTATION.md` created
- [x] `docs/architecture/MATCHING_RUNTIME_V1_SUMMARY.md` created
- [x] `docs/architecture/MATCHING_RUNTIME_V1_HANDOFF.md` created
- [x] `tests/test_matching_runtime.py` added and validated
- [x] Workflow stage integration validated by tests
- [x] `MatchType` integrated into result objects and strategy metadata
- [x] Historical match keying fixed to normalized entity signatures
