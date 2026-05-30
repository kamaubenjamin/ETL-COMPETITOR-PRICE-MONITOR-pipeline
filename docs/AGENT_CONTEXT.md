# Agent Context

This file provides future agents with the project context needed to continue development without prior conversation history.

## Project Vision

Build an Intelligent Document Processing Platform that ingests documents, extracts structured business entities, reconciles them against master data, and supports review and automation workflows. The platform is designed to be deterministic, auditable, and modular.

## Current Architecture

The platform is organized into layered runtimes:
- Document Runtime
- Workflow Runtime
- Entity Runtime
- Matching Runtime
- Review Runtime
- API Runtime
- Monitoring Runtime

Core architecture documents are stored in `docs/architecture`. Decision records are stored in `docs/adr`.

## Runtime Overview

- Document Runtime: ingests raw documents and produces normalized document artifacts.
- Workflow Runtime: orchestrates stage-based execution and artifact handoff.
- Entity Runtime: converts documents into immutable entities such as Customer, Supplier, and LineItem.
- Matching Runtime: reconciles entities against master data using exact, normalized, fuzzy, and historical strategies.
- Review Runtime: captures human review feedback and correction lifecycle.
- API Runtime: exposes external requests and responses for platform integration.
- Monitoring Runtime: observes runtime health and execution metrics.

## Repository Structure

Key documentation and code locations:
- `docs/architecture/`: architecture design and runtime boundaries
- `docs/adr/`: architecture decision records
- `docs/ROADMAP.md`: repository-level roadmap
- `docs/TECHNICAL_DEBT.md`: technical debt register
- `src/`: platform source code and runtime implementation
- `tests/`: automated tests

## Implemented Components

Current architecture coverage includes:
- Document Runtime architecture and foundational design
- Workflow Runtime architecture and stage orchestration design
- Entity Runtime v1 architecture, extraction contracts, and integration
- Matching Runtime v1 architecture with strategy and confidence design
- ADRs for workflow, entity, customer entity, party abstraction, and historical matching

## Current Milestone

The current milestone is architecture completion. Foundational runtime boundaries, ADR coverage, and onboarding documentation are being finalized.

## Outstanding Work

- Finalize Review Runtime and API Runtime architecture documents
- Define runtime boundaries and monitoring architecture
- Add agent-facing onboarding and ADR index references
- Update roadmap and technical debt register with the architecture completion milestone

## Known Limitations

- Workflows lack a formal review feedback loop in implementation
- Matching history is currently scoped to in-memory workflow sessions only
- Entity extraction uses heuristic parsing with limited validation coverage
- API Runtime and Monitoring Runtime are architectural concepts, not implemented runtime code

## Technical Debt Summary

Key debt areas:
- Document parsing heuristics and normalization coverage
- Workflow engine state, retries, and contract standardization
- Entity validation and confidence calibration
- Matching persistence, ERP integration, and review feedback loops
- API versioning, authentication hardening, and monitoring support

## Coding Standards

- Prefer deterministic, explainable runtime behavior
- Keep runtime boundaries clear and avoid crossing layers
- Use immutable contracts for runtime artifacts where possible
- Document architectural decisions and runtime boundaries in `docs/architecture`
- Maintain auditability in match and review explanations

## ADR Index

Refer to the following ADRs:
- `docs/adr/ADR-001-WORKFLOW-RUNTIME-V1.md`
- `docs/adr/ADR-002-ENTITY-RUNTIME-V1.md`
- `docs/adr/ADR-003-CUSTOMER-AS-CORE-ENTITY.md`
- `docs/adr/ADR-004-NO-PARTY-ABSTRACTION-V1.md`
- `docs/adr/ADR-005-MATCHING-RUNTIME-HISTORICAL-STRATEGY.md`
- `docs/adr/ADR-006-DOCUMENT-RUNTIME-V1.md`
- `docs/adr/ADR-007-API-RUNTIME-V1.md`
- `docs/adr/ADR-008-REVIEW-FEEDBACK-RUNTIME.md`

## Recommended Reading Order

1. `AGENT_CONTEXT.md`
2. `docs/architecture/RUNTIME_BOUNDARIES.md`
3. `docs/adr/ADR-006-DOCUMENT-RUNTIME-V1.md`
4. `docs/adr/ADR-007-API-RUNTIME-V1.md`
5. `docs/adr/ADR-008-REVIEW-FEEDBACK-RUNTIME.md`
6. `docs/architecture/ENTITY_RUNTIME_V1_ARCHITECTURE.md`
7. `docs/architecture/MATCHING_RUNTIME_V1_ARCHITECTURE.md`
8. `docs/architecture/README.md`
9. `docs/ROADMAP.md`
10. `docs/TECHNICAL_DEBT.md`

## Next Recommended Milestones

- Review Runtime implementation and feedback integration
- API Runtime implementation and external interface validation
- Monitoring Runtime design and observability integration
- ERP Runtime architecture and persistence strategy
- Agent Runtime architecture and automation contracts
