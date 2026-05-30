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

## Current Milestone

### Matching Runtime

Status:
- Active architecture and design phase
- Document-level roadmap and strategy are defined in `docs/architecture/MATCHING_RUNTIME_V1_ARCHITECTURE.md`

Objectives:
- Reconcile extracted entities against master data sources
- Support exact, normalized, fuzzy, and historical matching strategies
- Compute deterministic, explainable confidence scores
- Return immutable match results with audit explanations

Planned deliverables:
- Matching runtime architecture design
- `MatchRequest`, `MatchCandidate`, `MatchResult`, and `MatchSet` contracts
- Entity-specific confidence calculator design
- Historical match strategy defined as a first-class path
- Workflow integration points for the match stage

Dependencies:
- `Entity Runtime` output (`EntitySet`)
- `Workflow Runtime` stage orchestration
- Local or in-memory master data candidate sources

## Planned Milestones

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
2. Deliver `Review Runtime` for human exception handling and correction.
3. Build `ERP Runtime` for ERP source integration and reconciliation support.
4. Add `Agent Runtime` for automation, notification, and workflow orchestration.
5. Strengthen documentation, testing, and governance across runtime layers.
6. Validate end-to-end workflows with production-like data and regression suites.

The v1.0 goal is a stable, explainable ETL platform that can ingest documents, extract entities, reconcile against master data, and support governance-aware review and automation.
