# Contract Registry — README (v1)
Purpose
-------
This folder is the repository-centric Contract Registry v1. It stores canonical JSON Schema (Draft 07) artifacts used across runtimes and documents publishing, validation and migration practices.

Versioning strategy
-------------------
- Semantic-style versioning: `MAJOR.MINOR.PATCH`.
- Each schema file contains a top-level `schema_id` and `schema_version` (and `$id` / `version`) to make versions discoverable by agents and CI.

Schema ownership
----------------
- Schemas are owned by runtime teams. Ownership metadata should be added in the schema header and in the schema registry README for each runtime folder.
- Default owners (to be updated by repo owners):
  - `entity_runtime/` — Entity Runtime team
  - `matching_runtime/` — Matching Runtime team
  - `review_runtime/` — Review Runtime team
  - `workflow_runtime/` — Workflow Runtime team

Compatibility rules
-------------------
- Follow the compatibility and versioning rules in `docs/architecture/CONTRACT_REGISTRY_V1_ARCHITECTURE.md`.
- Add a MAJOR bump and an ADR for breaking changes.

Validation process
------------------
- Local: use recommended validators (Python `jsonschema` or Node `ajv`) and author unit tests that validate example fixtures against the schema.
- CI: PRs that modify schemas must pass `contract-validation` CI job (not yet implemented in this scaffolding).

Migration process
-----------------
- Use phased rollouts: producers emit new `schema_version` while supporting the previous MAJOR for a retention window.
- Document migration steps and rollback guidance in schema-specific READMEs.

Registry layout
--------------
```
docs/contracts/
  registry_README.md
  entity_runtime/
  matching_runtime/
  review_runtime/
  workflow_runtime/
```

End of registry README.
