# Matching Runtime V1 Implementation

## Objective

Implement the first production-ready Matching Runtime layer to reconcile extracted entities against master data. The implementation provides deterministic candidate generation, multiple matching strategies, explainable confidence scoring, and integration with the workflow stage system.

## Scope Completed

- Added `src/matching_runtime` package with contracts, strategies, confidence, normalization, repositories, and service orchestration.
- Implemented `MatchType` enum and immutable match model contracts.
- Added `MatchingStage` as a workflow stage integration point for `EntitySet` and artifact dictionaries.
- Included exact, normalized, fuzzy, and historical matching strategies.
- Created in-memory master data and historical match stores for deterministic local development.
- Added `tests/test_matching_runtime.py` with coverage for core contracts, strategies, confidence calculators, matching service, and workflow stage integration.
- Validated implementation with `pytest` and confirmed 64 passing tests across matching and workflow runtime targets.

## Files Added

- `src/matching_runtime/contracts/match_request.py`
- `src/matching_runtime/contracts/match_type.py`
- `src/matching_runtime/models/match_candidate.py`
- `src/matching_runtime/models/match_explanation.py`
- `src/matching_runtime/models/match_result.py`
- `src/matching_runtime/models/match_set.py`
- `src/matching_runtime/strategies/exact_match_strategy.py`
- `src/matching_runtime/strategies/normalized_match_strategy.py`
- `src/matching_runtime/strategies/fuzzy_match_strategy.py`
- `src/matching_runtime/strategies/historical_match_strategy.py`
- `src/matching_runtime/confidence/customer_confidence_calculator.py`
- `src/matching_runtime/confidence/supplier_confidence_calculator.py`
- `src/matching_runtime/confidence/product_confidence_calculator.py`
- `src/matching_runtime/repositories/master_data_repository.py`
- `src/matching_runtime/repositories/historical_match_store.py`
- `src/matching_runtime/normalization/text_normalizer.py`
- `src/matching_runtime/services/matching_service.py`
- `src/workflow_runtime/operations/matching_stage.py`
- `tests/test_matching_runtime.py`

## Files Updated

- `src/workflow_runtime/operations/__init__.py`
- `docs/ROADMAP.md`

## Implementation Notes

- `MatchType` is now a first-class enum used across strategies and match results.
- Historical matching is keyed by deterministic normalized entity signatures instead of request IDs to allow reuse across requests with equivalent entity content.
- The matching service attempts strategies in order: exact, normalized, historical, fuzzy.
- Fuzzy matches use a threshold and fall back to a confidence score when field-specific confidence factors are zero.
- `MatchingStage` accepts both raw entity dictionaries and `EntitySet` artifacts, flattening entity payloads into match requests.

## Integration

- Workflow runtime stage registration now exposes `MatchingStage` through `src/workflow_runtime/operations/__init__.py`.
- The stage accepts either `EntitySet` or artifact dictionaries and produces `MatchSet` output.
- The service is built for local in-memory execution but can be extended to repository-backed master data sources.

## Tests

- `tests/test_matching_runtime.py` covers:
  - Contract serialization
  - Exact, normalized, fuzzy, and historical strategy behavior
  - Confidence calculator outputs for customer, supplier, and product data
  - Matching service end-to-end behavior
  - `MatchingStage` integration with raw dict and `EntitySet` inputs

## Known Limitations

- Master data sources are in-memory only.
- No ERP or external data adapters are implemented in v1.
- Historical match storage is session-local and not durable.
- Confidence calculators rely on limited fields and may underweight partial fuzzy signals.

## Next Steps

- Add durable historical storage or external match cache.
- Add ERP/master-data connectors and repository adapters.
- Add a `MatchRequest` strategy override to support custom per-entity matching profiles.
- Add UI/pass-through integration for manual review and low-confidence matches.
