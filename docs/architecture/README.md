# Architecture Overview

This directory contains architecture documentation for the ETL Banking platform. It is the primary entry point for future agents and developers who need to understand runtime design, package boundaries, and implementation details.

## Platform Overview

The current runtime stack includes:

- **Document Runtime**
- **Structural Runtime**
- **Validation Runtime**
- **Workflow Runtime**
- **Entity Runtime**

## Architecture Documents

- [ENTITY_RUNTIME_V1_ARCHITECTURE.md](./ENTITY_RUNTIME_V1_ARCHITECTURE.md)
- [ENTITY_RUNTIME_V1_IMPLEMENTATION.md](./ENTITY_RUNTIME_V1_IMPLEMENTATION.md)
- [ENTITY_RUNTIME_V1_SUMMARY.md](./ENTITY_RUNTIME_V1_SUMMARY.md)
- [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)

## Runtime Roadmap

### Completed

- Document Runtime
- Workflow Runtime
- Entity Runtime

### Planned

- Matching Runtime
- Review Runtime
- ERP Runtime
- Agent Runtime

## Agent Handoff Guidance

Future agents and developers should start with this file, then proceed in the following order:

1. `ENTITY_RUNTIME_V1_ARCHITECTURE.md` — understand Entity Runtime design and boundaries.
2. `ENTITY_RUNTIME_V1_IMPLEMENTATION.md` — review what was built and how the implementation was structured.
3. `ENTITY_RUNTIME_V1_SUMMARY.md` — get a concise summary of the Entity Runtime work.
4. `IMPLEMENTATION_SUMMARY.md` — read the overall implementation report for the Entity Runtime handoff.

For broader platform context, use the runtime files and any existing documentation in the repo root.
