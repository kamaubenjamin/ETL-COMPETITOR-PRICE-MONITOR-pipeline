# Durable Document State v1 Handoff

**Milestone:** v0.12
**State:** Implemented and verified; closed pending owner commit and tag

## Current State

Document State now supports deterministic in-memory repositories and file-backed SQLite repositories behind the same read/write protocols. SQLite includes explicit relational schema, checksum-verified migrations, immutable mapping, transactional writes, optimistic versions, append idempotency, and reopen durability. `compose_document_state()` explicitly selects a backend and never falls back silently.

No API, Streamlit, Query Facade, or workflow bootstrap automatically activates durable mode. SQLite remains local/dev infrastructure.

## Important Files

- `src/document_state/composition.py`: explicit `in_memory`/`sqlite` selection and frozen composition result.
- `src/document_state/repositories.py`: persistence-neutral read/write protocols.
- `src/document_state/repositories_in_memory.py`: deterministic process-local backend.
- `src/document_state/persistence/config.py`: validated backend configuration.
- `src/document_state/persistence/schema.py`: logical schema metadata.
- `src/document_state/persistence/migrations.py`: migration and ledger contracts.
- `src/document_state/persistence/sqlite/connection.py`: SQLite connection and transaction policy.
- `src/document_state/persistence/sqlite/schema.sql`: explicit relational schema.
- `src/document_state/persistence/sqlite/migrations.py`: ordered migration application and checksum verification.
- `src/document_state/persistence/sqlite/mappers.py`: record/column reconstruction and canonical metadata mapping.
- `src/document_state/persistence/sqlite/repositories.py`: durable read/write repository implementation.
- `tests/document_state/`: contracts, conformance, composition, persistence, transaction, concurrency, privacy, and boundary tests.
- `docs/adr/ADR-017-durable-document-state.md`: durable persistence decision.

## How To Verify

```text
python -m pytest tests/document_state -q
python -m pytest tests/workflow_runtime/query_facade -q
python -m pytest tests/api/document_intelligence tests/ui/streamlit tests/review_runtime -q
python scripts/verify_boundaries.py
python -m py_compile src/document_state/composition.py
python -m py_compile src/document_state/persistence/sqlite/repositories.py
python -m pytest -q
git diff --check
```

The full suite can regenerate `price_history.csv`, `src/canonical_products.json`, `src/schedules.json`, and `src/storage/workflow_history.json`. Restore only those known generated files when they were clean before the run.

## Extension Rules

- Preserve existing Document State records and repository protocols.
- Add future database engines under `src/document_state/persistence/`.
- Run the shared conformance suite against every repository implementation.
- Keep migrations ordered, immutable after application, checksum-verified, and transactional.
- Revalidate records before writes and reconstruct through contracts after reads.
- Keep mutable updates compare-and-swap and append-only writes idempotent.
- Select repositories only through explicit validated composition.
- Inject readers into `DocumentStateQueryFacadeAdapter`; do not make Query Facade import persistence.
- Supply writers to approved workflow/upload producers through write ports, not concrete repositories.

## What Not To Change

- Do not let API, Streamlit, or Workflow Query Facade import persistence modules directly.
- Do not silently fall back between SQLite and in-memory state.
- Do not represent SQLite as production-scale persistence.
- Do not store complete records as opaque JSON blobs.
- Do not store raw documents, rows, correction values, artifacts, stack traces, credentials, or storage details in query-facing tables.
- Do not add PostgreSQL/Supabase clients without a separately approved milestone.
- Do not modify legacy `src/api/app.py`, root `dashboard.py`, or competitor-price modules.

## Current Read Boundary

```text
Document Intelligence API
  -> FacadeDocumentIntelligenceProvider
  -> Workflow Query Facade
  -> DocumentStateQueryFacadeAdapter
  -> Document State repositories
  -> DocumentStateComposition
  -> SQLite durable backend OR in-memory backend
```

## Known Risks And Deviations

- SQLite is verified for local/dev durability and basic concurrent writes, not production-scale load.
- No production process bootstrap selects durable mode.
- No cross-record unit of work or outbox contract exists.
- Limit/offset pagination may degrade on large mutable datasets.
- Foreign-key parent requirements remain deferred because existing ports allow independent summary arrival.
- Backup, recovery, retention, archive, and legal-hold operations are undefined.
- Nine optional API transport tests remain skipped.
- Boundary verification reports two pre-existing U+FEFF parse warnings.

## Next Recommended Milestone

Plan production state activation before implementation. The next plan should decide whether to prioritize live upload/processing writer integration or PostgreSQL persistence, and must define composition ownership, auth/tenant boundaries, operational telemetry, backup/recovery, retention/legal hold, and encrypted raw blob separation. API mutation endpoints remain a separate decision.
