# Architecture Overview

This directory contains architecture documentation for the ETL Banking platform. It is the primary entry point for future agents and developers who need to understand runtime design, package boundaries, and implementation details.

## v0.21 Zero-Budget Hosted UAT

- [Deployment architecture](./ZERO_BUDGET_UAT_DEPLOYMENT_V1_PLAN.md)
- [Seven-phase implementation plan](./ZERO_BUDGET_UAT_DEPLOYMENT_V1_IMPLEMENTATION_PLAN.md)
- [ADR-026](../adr/ADR-026-zero-budget-vercel-supabase-uat.md)
- [Phase 6 hosted verification](../implementation/V0_21_PHASE_6_HOSTED_UAT_CLOSEOUT.md)
- [Phase 7 release handoff](../implementation/V0_21_PHASE_7_RELEASE_HANDOFF.md)
- [v0.21 release notes](../releases/v0.21-zero-budget-hosted-uat.md)

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
- [MATCHING_RUNTIME_V1_IMPLEMENTATION.md](./MATCHING_RUNTIME_V1_IMPLEMENTATION.md)
- [MATCHING_RUNTIME_V1_SUMMARY.md](./MATCHING_RUNTIME_V1_SUMMARY.md)
- [MATCHING_RUNTIME_V1_HANDOFF.md](./MATCHING_RUNTIME_V1_HANDOFF.md)
- [CONTRACT_REGISTRY_V1_ARCHITECTURE.md](./CONTRACT_REGISTRY_V1_ARCHITECTURE.md)
- [CONTRACT_REGISTRY_V1_IMPLEMENTATION.md](./CONTRACT_REGISTRY_V1_IMPLEMENTATION.md)
- [CONTRACT_REGISTRY_V1_SUMMARY.md](./CONTRACT_REGISTRY_V1_SUMMARY.md)
- [CONTRACT_REGISTRY_V1_HANDOFF.md](./CONTRACT_REGISTRY_V1_HANDOFF.md)
- [CI_CONTRACT_VALIDATION_V1_IMPLEMENTATION.md](./CI_CONTRACT_VALIDATION_V1_IMPLEMENTATION.md)
- [CI_CONTRACT_VALIDATION_V1_SUMMARY.md](./CI_CONTRACT_VALIDATION_V1_SUMMARY.md)
- [CI_CONTRACT_VALIDATION_V1_HANDOFF.md](./CI_CONTRACT_VALIDATION_V1_HANDOFF.md)
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
- Matching Runtime
- Contract Registry v1
- CI Contract Validation v1

### Architecture Completed

- Document Runtime Architecture
- Workflow Runtime Architecture
- Entity Runtime Architecture
- Matching Runtime Architecture
- Contract Registry v1 Architecture
- CI Contract Validation v1 Implementation
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
4. `CONTRACT_REGISTRY_V1_ARCHITECTURE.md` — understand schema governance and versioning.
5. `CONTRACT_REGISTRY_V1_IMPLEMENTATION.md` — review delivered registry artifacts and validation commands.
6. `CONTRACT_REGISTRY_V1_HANDOFF.md` — confirm remaining CI validation and compatibility work.
7. `CI_CONTRACT_VALIDATION_V1_IMPLEMENTATION.md` — review CI contract validation workflow design.
8. `CI_CONTRACT_VALIDATION_V1_HANDOFF.md` — confirm deferred compatibility and boundary-validation work.
9. `REVIEW_RUNTIME_IMPLEMENTATION.md` — review Review Runtime implementation details.
10. `REVIEW_RUNTIME_SUMMARY.md` — review Review Runtime summary and verification notes.
11. `REVIEW_RUNTIME_HANDOFF.md` — review Review Runtime handoff and next steps.
12. `IMPLEMENTATION_SUMMARY.md` — review the implementation-report-level summary.

For broader platform context, use the runtime files and any existing documentation in the repo root.
