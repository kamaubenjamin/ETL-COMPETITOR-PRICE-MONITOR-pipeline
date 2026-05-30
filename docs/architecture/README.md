# Architecture Overview

This directory contains architecture documentation for the ETL Banking platform. It is the primary entry point for future agents and developers who need to understand runtime design, package boundaries, and implementation details.

## Platform Overview

The current runtime stack includes:

- **Document Runtime**
- **Structural Runtime**
- **Validation Runtime**
- **Workflow Runtime**
- **Entity Runtime**
- **Matching Runtime**
- **Review Runtime**
- **API Runtime**
- **Monitoring Runtime**

## Architecture Documents

- [ENTITY_RUNTIME_V1_ARCHITECTURE.md](./ENTITY_RUNTIME_V1_ARCHITECTURE.md)
- [MATCHING_RUNTIME_V1_ARCHITECTURE.md](./MATCHING_RUNTIME_V1_ARCHITECTURE.md)
- [RUNTIME_BOUNDARIES.md](./RUNTIME_BOUNDARIES.md)
- [REVIEW_RUNTIME_IMPLEMENTATION.md](./REVIEW_RUNTIME_IMPLEMENTATION.md)
- [REVIEW_RUNTIME_SUMMARY.md](./REVIEW_RUNTIME_SUMMARY.md)
- [REVIEW_RUNTIME_HANDOFF.md](./REVIEW_RUNTIME_HANDOFF.md)
- [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)

## ADR Index

- `../adr/ADR-001-WORKFLOW-RUNTIME-V1.md`
- `../adr/ADR-002-ENTITY-RUNTIME-V1.md`
- `../adr/ADR-003-CUSTOMER-AS-CORE-ENTITY.md`
- `../adr/ADR-004-NO-PARTY-ABSTRACTION-V1.md`
- `../adr/ADR-005-MATCHING-RUNTIME-HISTORICAL-STRATEGY.md`
- `../adr/ADR-006-DOCUMENT-RUNTIME-V1.md`
- `../adr/ADR-007-API-RUNTIME-V1.md`
- `../adr/ADR-008-REVIEW-FEEDBACK-RUNTIME.md`

## Runtime Roadmap

### Completed

- Document Runtime
- Workflow Runtime
- Entity Runtime

### Architecture Completed

- Document Runtime Architecture
- Workflow Runtime Architecture
- Entity Runtime Architecture
- Matching Runtime Architecture
- API Runtime Architecture
- Review Runtime Architecture

### Planned

- Monitoring Runtime
- ERP Runtime
- Agent Runtime

## Agent Handoff Guidance

Future agents and developers should start with this file, then proceed in the following order:

1. `RUNTIME_BOUNDARIES.md` — understand runtime boundaries and allowed dependencies.
2. `ENTITY_RUNTIME_V1_ARCHITECTURE.md` — understand Entity Runtime design and boundaries.
3. `MATCHING_RUNTIME_V1_ARCHITECTURE.md` — understand Matching Runtime design and strategies.
4. `REVIEW_RUNTIME_IMPLEMENTATION.md` — review Review Runtime implementation details.
5. `REVIEW_RUNTIME_SUMMARY.md` — review Review Runtime summary and verification notes.
6. `REVIEW_RUNTIME_HANDOFF.md` — review Review Runtime handoff and next steps.
7. `IMPLEMENTATION_SUMMARY.md` — review the implementation-report-level summary.

For broader platform context, use the runtime files and any existing documentation in the repo root.
