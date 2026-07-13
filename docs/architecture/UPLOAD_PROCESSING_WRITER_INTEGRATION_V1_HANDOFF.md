# Upload-to-Processing Writer Integration v1 Handoff

**Milestone:** v0.13
**State:** Implemented and verified; closed pending owner commit and tag

## Current State

Document State now has runtime-neutral writer commands and internal writer services for all ten operational record families. Writers operate through explicitly injected repository ports and have verified parity across in-memory and SQLite compositions. Deterministic fixtures prove written state is visible through the Query Facade and existing API provider without changing API or Streamlit behavior.

Concrete runtime producer adapters are not implemented. The mutable document projection also remains `received`; lifecycle history is append-only and does not yet advance that snapshot.

## Important Files

- `src/document_state/writers/commands.py`: immutable normalized writer commands and artifact references.
- `src/document_state/writers/errors.py`: stable privacy-safe writer failures.
- `src/document_state/writers/results.py`: bounded operation outcomes.
- `src/document_state/writers/idempotency.py`: deterministic domain-separated key derivation.
- `src/document_state/writers/mappings.py`: governed stage/status/record mappings.
- `src/document_state/writers/ports.py`: structural internal writer boundaries.
- `src/document_state/writers/ingestion_writer.py`: ingestion and classification writes.
- `src/document_state/writers/processing_writer.py`: processing, validation, and matching writes.
- `src/document_state/writers/review_writer.py`: review, correction, and reprocess writes.
- `src/document_state/writers/workflow_writer.py`: workflow, lifecycle, and audit writes.
- `tests/document_state/writers/`: contracts, service, boundary, backend, retry, and integration coverage.
- `tests/document_state/writers/read_after_write_fixtures.py`: deterministic complete-lifecycle integration fixture.
- `tests/api/document_intelligence/test_writer_read_after_write_provider.py`: existing API-provider compatibility coverage.
- `docs/adr/ADR-018-upload-processing-writer-integration.md`: governing architecture decision.

## How To Verify

```text
python -m pytest tests/document_state/writers -q
python -m pytest tests/document_state -q
python -m pytest tests/api/document_intelligence -q
python -m pytest tests/workflow_runtime/query_facade tests/ui/streamlit tests/review_runtime -q
python scripts/verify_boundaries.py
python -m py_compile src/document_state/writers/ingestion_writer.py
python -m py_compile src/document_state/writers/processing_writer.py
python -m py_compile src/document_state/writers/review_writer.py
python -m py_compile src/document_state/writers/workflow_writer.py
python -m pytest -q
git diff --check
```

The full suite may regenerate `price_history.csv`, `src/canonical_products.json`, `src/schedules.json`, and `src/storage/workflow_history.json`. Restore only those known files when they were clean before verification.

## Extension Rules

- Keep producer-specific adapters in the producer runtime that owns the source result contract.
- Translate only approved public result fields into immutable writer commands; never serialize runtime results wholesale.
- Inject writer services and repository ports explicitly from composition.
- Preserve stable source IDs, timestamps, idempotency keys, and caller-visible expected versions across retries.
- Add stage/status mappings only through the governed catalog with deterministic tests.
- Run writer tests against both in-memory and SQLite backends.
- Verify read-after-write behavior through Query Facade and API provider projections after any mapping change.
- Design lifecycle-driven document snapshot advancement as an explicit state transition policy before implementing it.

## What Not To Change

- Do not give API, Streamlit, or Query Facade writer ports.
- Do not add public mutations as part of a producer adapter.
- Do not let writer services select, construct, or silently fall back between repository backends.
- Do not import runtime implementations, Query Facade, API/UI, SQLite implementations, storage, telemetry, FlowSync, or competitor-price modules from writer services.
- Do not store raw documents, rows, correction values, artifacts, paths, credentials, stack traces, or raw exceptions.
- Do not infer document snapshot advancement from arbitrary stage names.
- Do not modify legacy `src/api/app.py`, root `dashboard.py`, or competitor-price modules.

## Current Read-After-Write Boundary

```text
Producer / internal runtime output
  -> Document State writer services
  -> Document State repositories
  -> DocumentStateComposition
  -> SQLite durable backend OR in-memory backend
  -> DocumentStateQueryFacadeAdapter
  -> Workflow Query Facade
  -> Document Intelligence API
  -> Streamlit api_preview
```

## Privacy And Security Rules

- Commands and metadata must remain bounded and JSON-scalar-only where metadata is allowed.
- Persist safe codes and templates, never source exception text.
- Artifact references are opaque identifiers, not paths, URLs with credentials, or payloads.
- Correction summaries never contain old or new values.
- Audit metadata remains allowlisted and scalar.

## Known Risks And Deviations

- Document lifecycle events do not advance the mutable document projection.
- Concrete producer adapters and application bootstrap wiring are absent.
- Multi-record writes are replay-safe checkpoints, not one atomic unit of work.
- No transactional outbox or distributed delivery guarantee exists.
- Opaque artifact references are validated but not persisted without an approved field.
- SQLite remains a local/dev backend.
- Nine optional API transport tests remain skipped.
- Boundary verification reports two pre-existing U+FEFF parse warnings.

## Next Recommended Milestone

Plan a narrow runtime producer-adapter and lifecycle-projection milestone. It should define producer ownership, composition/bootstrap injection, a governed document status transition model, retry behavior when lifecycle and snapshot writes diverge, and read-after-write acceptance tests. Public mutation endpoints, upload UI, auth/tenant policy, and raw blob storage should remain separate decisions.
