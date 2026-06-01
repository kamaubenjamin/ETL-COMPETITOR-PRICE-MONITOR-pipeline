# Release
contract-registry-v1

# Added

- Repository-centric Contract Registry v1 under `docs/contracts/`
- JSON Schema Draft 07 contracts for Entity, Matching, Review, and Workflow runtime artifacts
- Example fixtures for every registered v1 contract
- Contract validation tests under `tests/contracts/`
- Standalone validation script at `scripts/validate_contracts.py`
- Contract Registry v1 implementation, summary, and handoff documents

# Changed

- Roadmap now records Contract Registry v1 as a completed v0.5 Runtime Hardening foundation deliverable.
- Technical debt now distinguishes the closed registry gap from remaining CI validation and compatibility work.

# Tests

- `pytest tests/contracts -v`
- `python scripts/validate_contracts.py`

# Known Limitations

- CI Contract Validation is not yet implemented.
- Schema compatibility diffing against a released baseline is not yet implemented.
- Runtime producer and consumer validation remains optional.
- No external schema registry API exists in v1.

# Next Objective

CI Contract Validation
