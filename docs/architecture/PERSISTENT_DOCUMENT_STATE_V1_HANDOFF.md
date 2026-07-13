# Persistent Document State v1 Handoff

**Milestone:** v0.11
**State:** Implemented and verified; closed pending owner commit and tag

## Current State

Document State provides immutable persistence-neutral records, separate read/write ports, deterministic in-memory repositories, file-backed SQLite repositories, and a read-only adapter into the Workflow Query Facade. `compose_document_state()` now explicitly selects `in_memory` or `sqlite` and exposes separate reader/writer surfaces. No API/UI provider is wired to this selection automatically, and no live writer, API mutation, PostgreSQL, or production deployment is included.

## Important Files

- `src/document_state/__init__.py`: public Document State exports.
- `contracts.py`: enums, filters, and deterministic ordering contracts.
- `records.py`: immutable operational state records.
- `privacy.py`: safe metadata and value validation.
- `pagination.py`: bounded repository pagination.
- `errors.py`: stable repository-safe errors.
- `repositories.py`: separated structural read/write ports.
- `repositories_in_memory.py`: deterministic process-local repository implementation.
- `composition.py`: explicit validated in-memory/SQLite selection with no fallback.
- `persistence/sqlite/`: local/dev durable connection, migrations, mappers, schema, and repositories.
- `adapters/query_facade_adapter.py`: read-only mapping into public v0.10 read models.
- `tests/document_state/`: contracts, repositories, adapter, privacy, and boundary coverage.
- `docs/adr/ADR-016-persistent-document-state.md`: package ownership and persistence decisions.

## Verification Commands

```text
python -m pytest tests/document_state -q
python -m pytest tests/workflow_runtime/query_facade -q
python -m pytest tests/api/document_intelligence tests/ui/streamlit tests/review_runtime -q
python scripts/verify_boundaries.py
python -m py_compile src/document_state/repositories_in_memory.py
python -m py_compile src/document_state/adapters/query_facade_adapter.py
python -m pytest -q
git diff --check
```

The full suite can regenerate `price_history.csv`, `src/canonical_products.json`, `src/schedules.json`, and `src/storage/workflow_history.json`. Restore only those known generated files when they were clean before the run.

## Extension Rules

- Add persistence implementations behind the existing repository ports.
- Keep domain contracts independent of database libraries and schema tooling.
- Write operational updates through narrow Document State write ports; do not expose repository implementations to producers.
- Read API-facing state through `DocumentStateQueryFacadeAdapter` and the Workflow Query Facade.
- Preserve immutable records, bounded pagination, deterministic ordering, optimistic versions, append idempotency, and safe coded errors.
- Add concurrency, privacy, unavailable-source, migration, and full-regression tests for every durable implementation.
- Introduce production source selection only in an explicit composition root.
- Use `compose_document_state(PersistenceConfig(...))` for explicit repository construction; never infer a backend from consumer imports.

## What Not To Change

- Do not let API, Streamlit, or future FlowSync import Document State directly.
- Do not add Workflow Runtime implementation imports to Document State core.
- Do not expose raw documents, rows, correction values, artifact payloads, stack traces, storage paths, or arbitrary metadata in query-facing records.
- Do not put raw encrypted blobs in Document State read-model repositories.
- Do not collapse read and write ports into generic CRUD.
- Do not represent the in-memory implementation as durable or production-ready.
- Do not modify legacy `src/api/app.py`, root `dashboard.py`, or competitor-price modules as part of Document State work.

## API And UI Boundary

The approved read direction is:

```text
API / Streamlit
  -> Document Intelligence API
  -> FacadeDocumentIntelligenceProvider
  -> Workflow Query Facade
  -> DocumentStateQueryFacadeAdapter
  -> Document State read repositories
```

The API retains HTTP ownership. Streamlit and future FlowSync Document Intelligence remain API consumers. Existing FlowSync Competitor Price remains separate.

## Privacy And Security Rules

- Persist only bounded operational summaries in query-facing repositories.
- Keep raw correction values and source rows outside public projections.
- Use opaque stable IDs and safe lineage references.
- Never persist exception text or stack traces as public errors.
- Keep metadata scalar, bounded, and allowlisted.
- Design any future raw blob boundary separately with encryption, access control, retention, and audit policy.

## Known Risks And Deviations

- In-memory state remains process-local and volatile; SQLite is durable local/dev state but is not the production concurrency target.
- Atomicity is one repository operation; cross-record units of work remain undefined.
- Cross-record transactions, isolation, outbox delivery, backup, and recovery are undefined.
- Package-level composition exists, but no application bootstrap selects it for API/UI or live workflow writers.
- Identity, authorization, tenant partitioning, retention, and operational telemetry are absent.
- Limit/offset pagination may not suit large mutable production datasets.
- Nine optional API transport tests remain skipped.
- Boundary verification reports two pre-existing U+FEFF parse warnings.

## Next Recommended Milestone

Close v0.12 with final verification, summary, release notes, and durable-state handoff. PostgreSQL, production bootstrap activation, tenant/auth policy, retention execution, encrypted blob storage, telemetry, live upload/processing writers, and API mutation endpoints remain separate future decisions.
