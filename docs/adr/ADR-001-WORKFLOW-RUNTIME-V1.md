# Status
Accepted

# Context
The ETL Banking platform requires a modular runtime to execute stage-based pipelines. Existing architecture and workflow integration rely on a stage registry, dependency resolution, and clear artifact boundaries.

# Decision
Workflow Runtime v1 is implemented as a stage orchestration engine that supports registration and execution of individual stages such as `entity_extract` and `match`. The runtime maintains stage dependencies and passes immutable artifacts between stages.

# Consequences
Benefits:
- Enables incremental delivery by isolating runtime stages.
- Provides a clear integration point for Entity Runtime and future Matching Runtime.
- Supports deterministic workflow execution with explicit stage contracts.

Tradeoffs:
- Does not yet support advanced state management, retries, or branching.
- Stage contracts are minimally formalized, requiring careful extension for future stages.

Future implications:
- Future refinements should add richer lifecycle hooks, retry and error recovery, and a contract registry for stage inputs/outputs.
