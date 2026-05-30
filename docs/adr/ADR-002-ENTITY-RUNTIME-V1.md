# Status
Accepted

# Context
The platform needs a deterministic extraction layer between Document Runtime output and workflow execution. Entity Runtime must convert parsed document content into immutable business entities consumed by downstream stages.

# Decision
Entity Runtime v1 is structured as a dedicated runtime with extraction, validation, normalization, confidence, and orchestration subpackages. It exposes immutable contracts such as `EntitySet`, `Customer`, `Supplier`, `LineItem`, and `DocumentReference` and integrates through the existing `entity_extract` workflow stage.

# Consequences
Benefits:
- Creates a clean boundary between parsed documents and structured entities.
- Enables deterministic extraction and audit-friendly entity contracts.
- Allows workflow stages to rely on stable entity payloads.

Tradeoffs:
- Extraction uses heuristic and regex-based logic rather than full schema-aware parsing.
- Validation is intentionally lightweight for delivery speed.

Future implications:
- Future versions should add richer normalization, schema mapping, and stronger entity validation.
