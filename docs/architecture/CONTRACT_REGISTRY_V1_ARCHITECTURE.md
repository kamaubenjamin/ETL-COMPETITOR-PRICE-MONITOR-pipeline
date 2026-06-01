# Contract Registry v1 — Architecture
Date: 2026-06-01

Purpose
-------
Define the architecture for a Contract Registry (v1) to govern canonical contracts (JSON schemas) used across runtimes. The registry is the foundation for contract validation, CI gating, runtime boundary verification, and safe schema evolution.

Scope
-----
This document covers contracts for the following runtimes:
1. Entity Runtime contracts
2. Matching Runtime contracts
3. Review Runtime contracts
4. Workflow Runtime contracts

Goals
-----
- Provide a single source of truth for public schemas and contracts used by producers and consumers.
- Enable schema versioning and compatibility checks.
- Integrate contract validation into CI pipelines to prevent breaking changes.
- Provide clear migration and deprecation patterns to reduce runtime outages.

Contract Versioning Strategy
----------------------------
- Use semantic-style versioning for schemas: `MAJOR.MINOR.PATCH`.
  - MAJOR: incompatible (breaking) changes to schema (e.g., field type change, required field removed).
  - MINOR: additive, backwards-compatible changes (e.g., new optional fields).
  - PATCH: documentation or non-breaking clarifications, examples, default fixes.
- Each schema file must include a canonical `id` and `version` metadata field (e.g., `"$id": "urn:project:entity:extracted_entity:1.2.0"`).
- Every schema change must include a short compatibility statement in the schema header and an ADR when introducing a MAJOR change.

Schema Storage Structure
------------------------
Canonical storage layout (under repository) — this layout is intentionally file-centric so it is discoverable by agents and humans:

```
docs/contracts/
  entity_runtime/
    extracted_entity.schema.json
    entity_set.schema.json
  matching_runtime/
    match_result.schema.json
    match_candidate.schema.json
  review_runtime/
    review_event.schema.json
    review_decision.schema.json
  workflow_runtime/
    workflow_config.schema.json
    job_status.schema.json
  registry_README.md
```

- Each schema file is named using the canonical resource name and contains an embedded `version` value.
- `registry_README.md` describes publishing conventions, schema lifecycle, and validation commands.

Serialization Standards
----------------------
- Primary serialization: JSON (UTF-8) using JSON Schema for structural contracts.
- Event envelope pattern for message buses (recommended fields):
  - `schema_id` — canonical `$id` or name
  - `schema_version` — MAJOR.MINOR.PATCH
  - `payload` — the JSON object validated against the schema
  - `metadata` — provenance fields (producer_id, timestamp, source)
- For binary or high-throughput needs consider Avro/Protobuf in v2. The v1 registry accepts JSON Schema and documents migration paths to binary formats.

Backward Compatibility Rules
----------------------------
- Backward-compatible (allowed without MAJOR bump):
  - Add new optional fields
  - Add new enum values where consumers treat unrecognized values safely
  - Add additional non-required nested structures
- Breaking changes (require MAJOR bump and ADR):
  - Remove or rename fields
  - Change field types
  - Change semantics of existing fields
- Deprecation policy:
  - Mark fields as `deprecated` in schema documentation and add a deprecation timeline in the registry README.
  - Maintain support for the previous MAJOR version for a defined retention window (e.g., 3 months or two releases) before removal.

Contract Validation Strategy
---------------------------
- Validation at development-time:
  - Producers must validate example outputs against the relevant schema before committing changes.
  - Unit tests should include schema conformance tests using sample fixtures.
- Validation at runtime (recommended):
  - Consumers should validate incoming artifacts against an accepted schema version and log/metric any violations.
  - Producers may emit a `schema_version` header so consumers can select appropriate validator.
- Compatibility checks:
  - Implement a compatibility checker that ensures a new schema is compatible with the last released MAJOR/MINOR as per rules above.

CI Validation Strategy
----------------------
- Add a `contract-validation` CI job that runs on pull requests and releases:
  1. Lint schemas (JSON Schema linting).
  2. Run compatibility checks against the published baseline (last released schemas).
  3. Run producer fixture validations: execute small scripts that generate sample artifacts and validate against the target schema.
  4. Fail PRs that introduce incompatible changes without an ADR and explicit MAJOR version bump.
- Provide developer tooling (`scripts/validate_contracts.py` or `npm` toolchain) to make local validation easy.

Runtime Integration Strategy
---------------------------
- Publication:
  - Producers commit schema updates to `docs/contracts/` and open PRs. CI runs compatibility checks.
  - After review, PR merges update schemas and tag releases.
- Message bus integration:
  - Use the event envelope pattern; include `schema_id` and `schema_version` in headers or envelope metadata.
  - Consumers prefer explicit schema version matching; if unable to parse, emit a contract-violation metric and send to dead-letter queue.
- Consumer strategy:
  - Consumers should accept a range of minor versions within the same MAJOR during migration.
  - Implement translation adapters when a schema change requires mapping logic.

Migration Strategy
------------------
- Phased rollout:
  1. Author new schema (MAJOR.MINOR.PATCH). Add schema to `docs/contracts/` and increment version.
  2. Update producers to emit new `schema_version` while continuing to support the previous MAJOR for the retention window.
  3. Update consumers to accept new fields and validate with new schema.
  4. Remove support for old MAJOR after retention window and announce via release notes and ADR.
- Rollback plan:
  - Revert producer changes and re-deploy quickly if serious compatibility issues appear.
  - Use feature flags or configuration toggles during rollout to control exposure.

Technical Risks
---------------
- Multiple language runtimes may interpret JSON Schema drafts differently — pick a common draft and document tooling.
- Human errors during schema changes can cause broad breakage; mitigate via CI and guardrails.
- Storage and discoverability: large number of schemas requires clear naming and discovery patterns.
- Operational complexity if moving to binary formats later.

Success Criteria
----------------
- >90% of public artifacts validated by schema and run through CI contract tests.
- CI rejects incompatible schema changes unless accompanied by MAJOR bump and ADR.
- Consumers report <1% contract validation errors in staging during rollouts.
- Migration windows are respected (no unexpected breaking changes after GA).

Future Evolution
----------------
- v2: Add an automated schema registry API/service (Confluent Schema Registry or similar) for programmatic lookup and compatibility checks.
- v2: Support Avro/Protobuf artifacts and cross-serialization adapters.
- v2: Provide a schema discovery UI and a machine-readable catalog (OpenAPI-like index).

---

Implementation Recommendation
-----------------------------
- Start with a repo-centric registry (schemas in `docs/contracts/`) and an automated CI validation job. This minimizes infra changes and enables rapid adoption.
- Select JSON Schema Draft 07 as the canonical schema draft for v1 (broad language support), document this in `registry_README.md` and include validation tool recommendations (e.g., `jsonschema` for Python, `ajv` for Node).
- Implement the contract-validation CI job as the first step (block PRs for incompatible changes). Then roll out producer and consumer validation gradually.

---

End of document.
