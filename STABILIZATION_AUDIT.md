STABILIZATION AUDIT — Matching & Transform Stabilization

Date: 2026-06-01
Repo: ETL Banking

Summary
-------
This audit analyzes two failing areas surfaced while running the repository test-suite:

1. A runtime failure surfaced in a real-world scenario test (`test_realworld_scenario.py`) raising KeyError: 'technology' originating in `src/transform/intelligence_engine.py`.
2. A unit test import failure in `tests/test_comparison_engine.py` where `normalize_name` could not be imported from `src/transform/comparison_engine.py`.

The objective is to determine root causes, expected behavior, and the safest corrective actions without changing runtime code in this audit step.

Failing Tests (as reported)
---------------------------
- tests/test_realworld_scenario.py — KeyError: 'technology' (location: `src/transform/intelligence_engine.py`)
- tests/test_comparison_engine.py — ImportError: cannot import name 'normalize_name' (location: `src/transform/comparison_engine.py`)

Context observed during investigation
------------------------------------
- `src/transform/intelligence_engine.py` contains advanced product normalization and canonical name templates. The `canonical_forms` mapping for category 'tv' includes a format placeholder `{technology}`.
- `create_canonical_name()` in `intelligence_engine.py` calls `template.format(brand=..., size=..., model=..., **features.get('specifications', {}))`.
  - If `features['specifications']` lacks the `technology` key (common when technology cannot be extracted), Python's `str.format()` raises a KeyError for the missing placeholder.
- `src/transform/product_normalizer.py` implements `normalize_name`, `extract_brand`, `detect_category`, `extract_features`, and related utilities.
- `src/transform/comparison_engine.py` currently does not define `normalize_name` and friends; tests expect `comparison_engine` to re-export or provide `normalize_name`, `extract_brand`, `detect_category`, and `extract_features`.

Root Causes
-----------
1) KeyError: 'technology' in `intelligence_engine.create_canonical_name`
   - Cause: `create_canonical_name()` applies `str.format()` to a template that contains placeholders (e.g., `{technology}`) while unpacking only the `specifications` dict. When the `specifications` dict does not contain `technology`, `str.format()` raises a KeyError.
   - Why it surfaced: Some test inputs or real-world strings do not include detectable `technology` tokens (e.g., 'QLED', 'OLED', 'IPS'), so specs lack `technology`. The code assumes the template's named fields will always exist in the provided mapping.

2) ImportError: `normalize_name` not found in `comparison_engine`
   - Cause: `comparison_engine.py` does not export (or import-and-re-export) normalization helpers like `normalize_name`. Those helper functions live in `src/transform/product_normalizer.py`.
   - Why it surfaced: Tests import `normalize_name` and other helper functions from `src.transform.comparison_engine`, expecting a stable API surface. The file-level API contract changed (either by refactor or oversight), causing import failure in tests.

Expected behavior
-----------------
- `create_canonical_name()` should generate canonical names safely even when some specification fields are missing. Missing specification placeholders should be treated as empty strings (or otherwise defaulted) rather than causing exceptions.
- `src.transform.comparison_engine` should provide or re-export normalization/extraction helpers used by tests and other modules, or tests should import directly from the canonical `product_normalizer` module. The public API should be stable and documented.

Safest Fixes (recommended)
--------------------------
Note: All fixes below are low-risk, localized, and reversible. They are presented in order of safety.

A) Fix KeyError in `create_canonical_name()` (safest)
   - Change `create_canonical_name()` to use a safe mapping with defaults when formatting templates. Options:
     1. Use `template.format_map(defaultdict(str, mapping))` so missing keys produce an empty string instead of KeyError.
     2. Build an explicit formatting dict that includes defaults for known template keys (e.g., `technology`, `storage`, `ram`) before calling `format()`.
   - Rationale: minimal, deterministic change; avoids exceptions and preserves intended template output semantics. No behavior change for inputs that contain the spec.
   - Example (pseudocode):
     - specs = features.get('specifications', {})
     - format_map = {**{'technology': '', 'storage':'', 'ram':''}, **specs, 'brand':brand, 'size':size, 'model':model}
     - return template.format_map(format_map)

B) Harden `extract_specifications()` to always include expected keys
   - Ensure `extract_specifications()` returns a dictionary that always contains keys used by templates (e.g., `technology`, `storage`, `ram`) with None or empty-string defaults.
   - Rationale: increases predictability of `specifications` shape and helps downstream code, but slightly larger surface area than the formatting fix.

C) Restore expected public API for `comparison_engine`
   - Option 1 (recommended): Reintroduce re-exports at top of `src/transform/comparison_engine.py`:
     - from src.transform.product_normalizer import normalize_name, extract_brand, detect_category, extract_features
     - Then add these names to module exports (implicitly available).
   - Option 2: Update tests to import helpers from `src.transform.product_normalizer` directly (requires coordinated test changes).
   - Rationale: Re-export keeps older import paths working and is low-risk. Changing tests is higher risk and broader.

D) Add a small unit test for canonical formatting edge-cases
   - Test that `create_canonical_name()` produces reasonable output when `specifications` is missing keys.
   - Rationale: prevents regression and documents expected behavior.

Risk Assessment
---------------
- Fix A (format_map/defaults): Very low risk. Localized change in `create_canonical_name()`; preserves behavior for correct inputs and prevents KeyError on missing specs. No dependency ripple expected.
- Fix B (normalize extract_specifications shape): Low risk but touches extraction logic; should be accompanied by unit tests. May slightly alter outputs (spec keys set to empty string vs absent), which can affect template formatting or equality checks elsewhere.
- Fix C (re-export functions in `comparison_engine`): Very low risk. Restores backwards-compatible API surface and resolves ImportError without changing normalization logic. Minimal chance of unintended side effects.
- Fix D (tests): No risk — adds coverage.

Impact on New Runtimes (Matching, Workflow, Review)
-------------------------------------------------
- Matching Runtime: The canonical name generator is used in product canonicalization and matching decisions (via `duplicate_reducer` and `find_canonical_match`). Preventing KeyErrors stabilizes processing pipelines and reduces unexpected workflow stage failures. Defaulting missing spec fields will not significantly change matching behavior but will avoid crash-on-missing-data scenarios.
- Workflow Runtime: `MatchingStage` and downstream stages that expect stable `canonical_name`/`canonical_id` will no longer encounter unhandled exceptions for missing specifications. Stage reliability increases.
- Review Runtime: Not implemented yet, but canonicalization stability reduces volume of noisy errors that would otherwise generate review tasks.

Proposed Action Plan (next steps)
---------------------------------
1. Implement Fix A (safe formatting defaults) in `src/transform/intelligence_engine.py`.
2. Add a unit test covering `create_canonical_name()` when `specifications` lacks `technology`.
3. Implement Fix C: re-export normalization helpers from `src/transform/comparison_engine.py` by importing them from `src/transform/product_normalizer.py` and leaving the public API stable.
4. Run full test-suite and verify all tests (including `tests/test_comparison_engine.py`, `tests/test_realworld_scenario.py`) pass.
5. Optionally implement Fix B if additional consumers require explicit spec keys.

Estimated Effort
----------------
- Code edits: 2–3 small edits (~20–40 lines total).
- Tests: 1 small unit test to cover canonical formatting; update if necessary to reflect behavior change (~10–20 lines).
- Validation: run full `pytest` suite (~1–5 minutes depending on environment).

Appendix — Evidence and snippets
--------------------------------
- Offending code (simplified):

    template = self.canonical_forms[category]
    return template.format(
        brand=brand,
        size=size,
        model=model,
        **features.get('specifications', {})
    )

  Failure mode: if `specifications` lacks `technology`, `format()` raises KeyError.

- Recommended safe formatting (pseudocode):

    specs = features.get('specifications', {}) or {}
    defaults = {'technology': '', 'storage': '', 'ram': ''}
    fmt = {**defaults, **specs, 'brand': brand, 'size': size, 'model': model}
    return template.format_map(fmt)

- `comparison_engine` test expectation: tests import `normalize_name` and friends from `src.transform.comparison_engine`. Provide re-exports:

    # at top of src/transform/comparison_engine.py
    from src.transform.product_normalizer import (
        normalize_name,
        extract_brand,
        detect_category,
        extract_features,
    )

Deliverable
-----------
This document is the requested stabilization audit. No code changes have been made as part of this audit — only analysis and recommendations are included.

Prepared by: automated repo auditor

