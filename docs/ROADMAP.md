# Repository Roadmap

## Purpose

This roadmap captures the long-term platform vision, runtime architecture, milestone progress, and planned work for the ETL Banking repository. It is written for Copilot, Cline, ChatGPT, Codex, and future developers who need a single, repo-level planning document.

## Vision

Build a production-ready ETL platform for pricing intelligence, supplier/customer reconciliation, and ERP-ready master data matching. The platform should support deterministic runtime layers, explainable decisions, reusable workflow stages, and a path to operational deployment with strong documentation, testing, and governance.

Key vision elements:
- End-to-end runtime architecture from document ingestion to master data matching
- Deterministic, auditable extraction and matching logic
- Modularity for future review, ERP, and agent-based automation layers
- Platform maturity aimed at v1.0 production deployment

## Runtime Architecture

The runtime stack is organized as a layered execution platform:

1. Document Runtime
2. Structural Runtime
3. Validation Runtime
4. Workflow Runtime
5. Entity Runtime
6. Matching Runtime
7. Review Runtime
8. ERP Runtime
9. Agent Runtime

Each runtime layer has a specific responsibility and clearly defined boundary, enabling incremental delivery and future extension.

## Completed Milestones

### Document Runtime

Purpose:
- Parse source documents and produce normalized document artifacts
- Extract sections, OCR/text, tables, and metadata for downstream processing

Delivered capabilities:
- Document ingestion pipeline
- Parsing and structure extraction
- Normalized document output for runtime consumption

### Workflow Runtime

Purpose:
- Execute stage-based ETL pipelines with configurable workflow definitions
- Orchestrate runtime stages such as extraction and matching

Delivered capabilities:
- Workflow stage registration and execution
- Stage dependency resolution
- Support for `entity_extract` and future runtime stages

### Entity Runtime

Purpose:
- Convert Document Runtime output into immutable entity contracts
- Validate, normalize, and score extracted business entities

Delivered capabilities:
- `EntityExtractionEngine` and package-level extraction architecture
- Immutable entity contracts in `src/entity_runtime/contracts`
- Validation, normalization, and confidence scoring modules
- Workflow integration via `entity_extract` stage

### Architecture Completion

Purpose:
- Establish baseline architecture coverage across major runtime boundaries
- Provide ADR records and onboarding documentation for future development
- Ensure runtime ownership and dependency direction are documented

Completed items:
- Workflow Runtime Architecture
- Entity Runtime Architecture
- Matching Runtime Architecture
- Document Runtime Architecture
- API Runtime Architecture
- Review Runtime Architecture
- Contract Registry v1 Architecture
- Runtime Boundaries document
- Agent onboarding context

## Latest Delivery

### v0.6 Extraction & Transformation Capability Hardening

Status:
- Closed and tagged as `v0.6-extraction-transformation-capability-hardening`
- Full regression and runtime-boundary verification pass

Delivered capabilities:
- Versioned deterministic transformation, mapping, validation, sorting, and aggregation contracts
- Real Workflow Runtime `transform`, `validate_data`, `sort`, and `aggregate` behavior
- Authoritative workflow stage catalog aligned with runtime registration and validation
- Privacy-safe metadata, immutable inputs, deterministic integration coverage, and legacy rule compatibility

References:
- `docs/architecture/EXTRACTION_TRANSFORMATION_CAPABILITY_HARDENING_V1_SUMMARY.md`
- `docs/architecture/EXTRACTION_TRANSFORMATION_CAPABILITY_HARDENING_V1_HANDOFF.md`
- `docs/adr/ADR-012-extraction-transformation-capability-hardening.md`
- `docs/releases/v0.6-extraction-transformation-capability-hardening.md`

### v0.7 Review / Correction Runtime

Status:
- Closed and tagged as `v0.7-review-correction-runtime`

Delivered capabilities:
- Deterministic review case lifecycle and reviewer decisions
- Field-level, version-aware corrections with append-only audit and lineage
- Non-blocking declarative reprocess requests and dry-run plans; execution remains Workflow-owned and deferred
- Backend source of truth for future Streamlit and FlowSync consumers

References:
- `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_PLAN.md`
- `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_SUMMARY.md`
- `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_HANDOFF.md`
- `docs/adr/ADR-013-review-correction-runtime.md`
- `docs/releases/v0.7-review-correction-runtime.md`

### v0.8 Document Intelligence Operator Console

Status:
- Closed and tagged as `v0.8-document-intelligence-operator-console`
- Live backend integration remains deferred to v0.9 and later milestones

Delivered capabilities:
- Separate Document Intelligence console beside the legacy competitor-price dashboard
- Operational overview, inbox, upload placeholder, processing, validation, matching, review, workflow, and audit views
- Display-only document and review lifecycle filters with no runtime mutation
- Local provider adapters, stable view models, reusable display components, and focused UI tests
- Review Queue and Audit Logs shaped from deterministic public Review Runtime contracts
- Consistent navigation, grouped workloads, status/priority labels, run-mode messaging, and filtered empty states
- No API, database, external service, OCR, or LLM dependency

References:
- `docs/architecture/DOCUMENT_INTELLIGENCE_OPERATOR_CONSOLE_V1_PLAN.md`
- `docs/architecture/DOCUMENT_INTELLIGENCE_OPERATOR_CONSOLE_V1_SUMMARY.md`
- `docs/architecture/DOCUMENT_INTELLIGENCE_OPERATOR_CONSOLE_V1_HANDOFF.md`
- `docs/releases/v0.8-document-intelligence-operator-console.md`

### v0.9 Document Intelligence API Foundation

Status:
- Architecture, implementation plan, and ADR complete
- Closed and tagged as `v0.9-document-intelligence-api-foundation`

Planned capabilities:
- Separate versioned read-only Document Intelligence API
- Health, document, processing, validation, matching, review, correction-history, reprocess-plan, workflow, and audit endpoints
- Deterministic providers and strict privacy-safe response contracts
- Streamlit API-provider preview and future FlowSync Document Intelligence consumer boundary
- R05-compliant integration through a future Workflow Runtime query facade

References:
- `docs/architecture/DOCUMENT_INTELLIGENCE_API_FOUNDATION_V1_PLAN.md`
- `docs/architecture/DOCUMENT_INTELLIGENCE_API_FOUNDATION_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/DOCUMENT_INTELLIGENCE_API_FOUNDATION_V1_SUMMARY.md`
- `docs/architecture/DOCUMENT_INTELLIGENCE_API_FOUNDATION_V1_HANDOFF.md`
- `docs/adr/ADR-014-document-intelligence-api-foundation.md`
- `docs/releases/v0.9-document-intelligence-api-foundation.md`

### v0.10 Workflow Query Facade

Status:
- Architecture, implementation plan, ADR, verification, summary, handoff, and release notes complete
- Closed and tagged as `v0.10-workflow-query-facade`

Planned capabilities:
- Workflow-owned public read facade under `src/workflow_runtime/query_facade/`
- Stable bounded read models for documents, processing, validation, matching, reviews, corrections, reprocess plans, workflow runs, and audit
- Deterministic in-memory facade and explicit API provider adapter
- Unchanged v0.9 API routes, envelopes, privacy behavior, pagination, and GET-only surface
- Narrow injected source ports with no direct cross-runtime implementation imports

References:
- `docs/architecture/WORKFLOW_QUERY_FACADE_V1_PLAN.md`
- `docs/architecture/WORKFLOW_QUERY_FACADE_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/WORKFLOW_QUERY_FACADE_V1_SUMMARY.md`
- `docs/architecture/WORKFLOW_QUERY_FACADE_V1_HANDOFF.md`
- `docs/adr/ADR-015-workflow-query-facade.md`
- `docs/releases/v0.10-workflow-query-facade.md`

### v0.11 Persistent Document State / Repository Layer

Status:
- Closed and tagged: `v0.11-persistent-document-state`
- All five phases complete: immutable contracts, deterministic in-memory repositories, a read-only Workflow Query Facade repository adapter, boundary/privacy/repository hardening, and release handoff

Planned capabilities:
- Persistence-neutral operational document state under `src/document_state/`
- Immutable records and explicit read/write repository ports for document, lifecycle, processing, validation, matching, review, correction, reprocess, workflow, and audit state
- Deterministic in-memory repositories with bounded pagination, stable ordering, idempotency, and optimistic version checks
- Injected repository adapter implementing public Workflow Query Facade ports
- Privacy-safe persistence with no raw document rows, correction values, artifact payloads, stack traces, or unrestricted metadata
- Unchanged v0.9 API contracts and v0.10 Query Facade read models

References:
- `docs/architecture/PERSISTENT_DOCUMENT_STATE_V1_PLAN.md`
- `docs/architecture/PERSISTENT_DOCUMENT_STATE_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/PERSISTENT_DOCUMENT_STATE_V1_SUMMARY.md`
- `docs/architecture/PERSISTENT_DOCUMENT_STATE_V1_HANDOFF.md`
- `docs/adr/ADR-016-persistent-document-state.md`
- `docs/releases/v0.11-persistent-document-state.md`

### v0.12 Durable Document State

Status:
- Architecture plan, implementation plan, and ADR proposed
- Phase 1 implemented: persistence configuration, safe errors, deterministic schema metadata, and immutable migration/ledger validation contracts
- Phase 2 implemented: file-backed SQLite repositories, explicit relational schema, transactional migrations, optimistic updates, append idempotency, and reopen durability
- Phase 3 implemented: shared in-memory/SQLite conformance, rollback and snapshot consistency, migration replay, and deterministic basic writer concurrency verification
- Phase 4 implemented: explicit validated in-memory/SQLite composition with separate read/write surfaces and no silent fallback or automatic consumer wiring
- Phase 5 pending

Planned capabilities:
- SQLite-backed local/dev durable repositories behind existing Document State ports
- Explicit relational schema and checksum-verified migration layout for all ten record families
- Transactional optimistic versioning and append idempotency
- Deterministic indexed filtering, ordering, and bounded pagination
- Shared in-memory/SQLite repository conformance tests
- Explicit in-memory versus SQLite repository selection with no silent fallback
- PostgreSQL production target and Supabase managed option deferred to later implementation
- Unchanged API, Query Facade, and Streamlit contracts and boundaries

References:
- `docs/architecture/DURABLE_DOCUMENT_STATE_V1_PLAN.md`
- `docs/architecture/DURABLE_DOCUMENT_STATE_V1_IMPLEMENTATION_PLAN.md`
- `docs/adr/ADR-017-durable-document-state.md`

## Prior Milestone Context

### v0.5 Runtime Hardening

Status:
- Active milestone
- Contract Registry v1 is formally closed
- CI Contract Validation v1 is implemented
- Runtime Boundary Verification v1 (Tier 1) is completed
- ✅ **Workflow Runtime Locking v1 is completed**
- ✅ **Entity Runtime Concurrency Hardening is completed**
- Next objective: Observability Improvements

Completed foundation deliverables:
- Contract Registry v1 with JSON Schema Draft 07 contracts, fixtures, local validation tests, and standalone validation script
- CI Contract Validation v1 with a lightweight GitHub Actions workflow for contract tests and standalone validation
- Runtime Boundary Verification v1 — Tier 1 Static Import Isolation Analysis
  - `scripts/verify_boundaries.py`: AST-based scanner for R01-R05, R12
  - `tests/boundaries/`: 22-test suite, exemption registry with 4 legacy entries
  - 0 active violations (compliant)
  - See `docs/architecture/RUNTIME_BOUNDARY_VERIFICATION_V1_SUMMARY.md`
- **Workflow Runtime Locking v1** — database-backed row-level locking with execution leases, file-based fallback, idempotency keys for deduplication, and comprehensive test suite (158/158 passing)
  - See `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_SUMMARY.md`
  - See `docs/adr/ADR-008-workflow-runtime-locking.md`

Next planned objectives:
1. ✅ **Workflow Runtime Locking** (completed)
2. ✅ **Entity Runtime Concurrency Hardening** (completed)
3. Observability Improvements
4. Review Runtime Audit Linking
5. Runtime Boundary Verification Tier 2 & 3 (future)

### Matching Runtime

Status:
- Released as v0.4
- Architecture baseline coverage is complete, with practice documents in place
- Document-level strategy is defined in `docs/architecture/MATCHING_RUNTIME_V1_ARCHITECTURE.md`
- Implementation validated with `tests/test_matching_runtime.py`

Objectives:
- Reconcile extracted entities against master data sources
- Support exact, normalized, fuzzy, and historical matching strategies
- Compute deterministic, explainable confidence scores
- Return immutable match results with audit explanations

Planned deliverables:
- Completed in v0.4 Matching Runtime release

Dependencies:
- `Entity Runtime` output (`EntitySet`)
- `Workflow Runtime` stage orchestration
- Local or in-memory master data candidate sources

## Planned Milestones

### CI Contract Validation

Purpose:
- Enforce Contract Registry v1 through hosted PR and release validation.
- Prevent incompatible schema changes from merging without versioning and ADR review.

Delivered capabilities:
- CI job for `pytest tests/contracts -v`
- CI job or step for `python scripts/validate_contracts.py`
- Minimal dependency install for `pytest` and `jsonschema`

Deferred capabilities:
- Schema compatibility checks against a released baseline
- Governance check for MAJOR schema changes and ADR presence

Dependencies:
- Contract Registry v1 schemas and fixtures
- Existing validation script and contract test suite

Status:
- Implemented as CI Contract Validation v1

### Review Runtime

Purpose:
- Provide human-review and exception management for unmatched or low-confidence entities
- Support review workflows, manual corrections, and audit handoff

Expected capabilities:
- Review queue generation from match results
- Manual override and match correction support
- Audit trail capture for review decisions
- Integration with workflow stage results

Dependencies:
- `Matching Runtime` for match result generation
- `Workflow Runtime` for review stage orchestration
- `Entity Runtime` for entity provenance

### ERP Runtime

Purpose:
- Enable ERP integration for master data lookup and downstream posting
- Support ERP-specific source/target mappings without mutating source documents

Expected capabilities:
- ERP master data source adapters
- Read-only ERP reconciliation support in v1
- Configurable ERP metadata and source selection

Dependencies:
- `Matching Runtime` for entity-to-master reconciliation
- `Workflow Runtime` for ERP stage orchestration
- ERP connection configuration and secure credential handling

### Agent Runtime

Purpose:
- Support automated agent workflows and decision automation on top of runtime outputs
- Provide structured automation for notifications, alerts, and corrective actions

Expected capabilities:
- Agent orchestration layer for rule-driven actions
- Triggered workflows based on match and review outcomes
- Integration points for policy-driven automation

Dependencies:
- `Workflow Runtime` for stage execution and event handling
- `Matching Runtime` and `Review Runtime` for decision context
- Platform governance and security policies

## Next Milestones

- Close and tag v0.7 Review / Correction Runtime after the Phase 5 documentation commit
- Plan durable Review Runtime persistence and trusted service boundaries
- Workflow Runtime Locking
- Entity Runtime Concurrency Hardening
- Observability Improvements
- Review Runtime Audit Linking
- Monitoring Runtime Architecture
- ERP Runtime Architecture
- Agent Runtime Architecture

## Cross-Cutting Initiatives

### Documentation

- Maintain architecture docs in `docs/architecture`
- Keep design docs aligned with runtime boundaries and current status
- Provide clear handoff guidance for future agents and developers

### Testing

- Add package-level and integration tests for runtime components
- Validate workflow stage behavior with `pytest` suites
- Keep deterministic behavior and contract boundaries covered

### Governance

- Define runtime boundaries and architecture decisions clearly
- Track milestone status and platform ownership
- Preserve design intent through documentation and review

### Security

- Avoid storing sensitive data in architecture docs
- Design future ERP and agent layers with secure configuration boundaries
- Keep runtime code separated from credential and external-service logic

### Release Management

- Use milestone-based delivery for runtime layers
- Validate completed features before advancing to the next milestone
- Keep roadmap aligned with production deployment goals

## Long-Term Goal

Path to v1.0 production deployment:

1. Finish `Matching Runtime` with deterministic, audited master data matching.
2. Complete v0.5 Runtime Hardening, starting with CI enforcement for Contract Registry v1.
3. Deliver `Review Runtime` for human exception handling and correction.
4. Build `ERP Runtime` for ERP source integration and reconciliation support.
5. Add `Agent Runtime` for automation, notification, and workflow orchestration.
6. Strengthen documentation, testing, and governance across runtime layers.
7. Validate end-to-end workflows with production-like data and regression suites.

The v1.0 goal is a stable, explainable ETL platform that can ingest documents, extract entities, reconcile against master data, and support governance-aware review and automation.
