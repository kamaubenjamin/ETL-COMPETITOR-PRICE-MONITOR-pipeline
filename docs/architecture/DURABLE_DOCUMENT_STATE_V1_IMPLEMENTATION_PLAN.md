# Durable Document State v1 Implementation Plan

**Milestone:** v0.12
**Status:** Phases 1-4 complete; Phase 5 pending

## 1. Milestone Overview

v0.12 adds a SQLite-backed local/dev implementation behind the v0.11 Document State repository interfaces, proves it with an engine-neutral conformance suite, and defines explicit backend selection. PostgreSQL remains the production target for a later milestone. Each phase is scoped to one Codex session and stops before the next phase.

No API endpoint, payload, Streamlit UI, upload processing, auth, tenant isolation, mutation endpoint, OCR, LLM, external service, PostgreSQL deployment, or Supabase integration is included.

## 2. Phase 1: Persistence Contracts, Schema Plan, And Migration Layout

**Completion note:** Added standard-library-only persistence configuration, safe error, logical schema, migration definition, applied-ledger, sequence, checksum, and engine validation contracts. The deterministic schema catalog covers all eleven planned tables and classifies keys, ordering, indexes, privacy, and mutable/append-only semantics. SQLite and future PostgreSQL are explicit; future PostgreSQL cannot be activated. Focused persistence tests: 30 passed. Full Document State suite: 127 passed. No SQL, database connection, file write, repository implementation, API/UI integration, dependency, or root public export was added.

### Objectives

- Add persistence-local configuration and connection/migration contracts without changing public repository ports.
- Create the persistence contract layout and logical schema metadata for all ten record families plus the migration ledger.
- Add migration ledger, checksum, ordering, gap, and newer-schema validation.
- Define explicit column mappings, canonical metadata JSON, internal idempotency fields, indexes, and foreign-key decisions.
- Keep migration execution and real SQL deferred to Phase 2.

### Expected Files

Create:

- `src/document_state/persistence/__init__.py`
- `src/document_state/persistence/config.py`
- `src/document_state/persistence/errors.py`
- `src/document_state/persistence/migrations.py`
- `src/document_state/persistence/schema.py`
- `src/document_state/persistence/sqlite/__init__.py`
- `tests/document_state/persistence/__init__.py`
- `tests/document_state/persistence/test_config.py`
- `tests/document_state/persistence/test_migrations.py`
- `tests/document_state/persistence/test_schema.py`
- `tests/document_state/persistence/test_boundaries.py`

Modify only if public persistence exports are required:

- `src/document_state/__init__.py`
- v0.12 planning/status documentation

### Tests

- Configuration rejects unknown backends and requires explicit SQLite file settings.
- Future PostgreSQL remains represented but deferred from active selection.
- Duplicate versions, gaps, checksum drift, and newer schemas fail safely.
- All planned table metadata includes keys, ordering, indexes, privacy, and semantics.
- Migration definitions and applied-ledger records are immutable and JSON-compatible.
- Persistence errors expose no path, SQL, values, or driver text.
- No database, file, network, repository, or execution behavior exists.

### Verification

```text
python -m pytest tests/document_state/persistence -q
python -m pytest tests/document_state -q
python scripts/verify_boundaries.py
python -m py_compile src/document_state/persistence/config.py
python -m py_compile src/document_state/persistence/migrations.py
python -m py_compile src/document_state/persistence/schema.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after persistence contracts, schema metadata, migration validation, and boundary verification. Do not create SQL, open databases, implement repositories, or add composition.

## 3. Phase 2: SQLite Durable Repository Implementation

**Completion note:** Added an explicit file-backed SQLite connection factory, transactional migration runner and ledger, canonical metadata mappers, relational schema for all ten record families, and separate read/write durable repository views. The implementation preserves v0.11 filters, ordering, pagination, optimistic versions, append idempotency, privacy validation, and immutable reconstruction. Focused Phase 2 tests: 20 passed. Full Document State suite: 147 passed.

### Objectives

- Implement all v0.11 read and write repository protocols with standard-library SQLite.
- Preserve deterministic filters, ordering, bounded pagination, and immutable reconstruction.
- Implement atomic create/get/list/update/append behavior across all ten record families.
- Enforce optimistic compare-and-swap updates.
- Enforce append idempotency using database unique constraints and canonical content hashes.
- Prove file reopen durability and safe source-unavailable behavior.

### Expected Files

Create:

- `src/document_state/persistence/sqlite/connection.py`
- `src/document_state/persistence/sqlite/migrations.py`
- `src/document_state/persistence/sqlite/mappers.py`
- `src/document_state/persistence/sqlite/repositories.py`
- `src/document_state/persistence/sqlite/schema.sql`
- `tests/document_state/persistence/test_sqlite_connection.py`
- `tests/document_state/persistence/test_sqlite_migrations.py`
- `tests/document_state/persistence/test_sqlite_repositories.py`

Modify:

- `src/document_state/persistence/sqlite/__init__.py`
- v0.12 planning/status documentation

### Tests

- Structural read/write protocol conformance and separation.
- Create/get/list/update/append behavior for every record family.
- All filters, deterministic orderings, totals, limits, and offsets.
- Duplicate IDs, missing IDs, invalid records/queries, and unavailable source.
- Database close/reopen preserves records and ordering.
- Returned records are immutable and no connection/SQL/path leaks.
- No API, UI, runtime implementation, competitor, network, or external-service imports.

### Verification

```text
python -m pytest tests/document_state/persistence/test_sqlite_repositories.py tests/document_state/persistence/test_sqlite_durability.py -q
python -m pytest tests/document_state -q
python -m pytest tests/workflow_runtime/query_facade -q
python scripts/verify_boundaries.py
python -m py_compile src/document_state/persistence/sqlite/repositories.py
git diff --check
git status --short --branch
```

### Stop Condition

Completed. Stop before shared conformance extraction, broader concurrent-connection hardening, composition, API wiring, live writers, or PostgreSQL.

## 4. Phase 3: Repository Conformance And Transaction Verification

**Completion note:** Added one parametrized repository contract suite covering in-memory and SQLite backends plus focused SQLite durability, transaction consistency, rollback, optimistic concurrency, and idempotency race tests. The tests use temporary file databases, barriers instead of sleeps, and no network or external service. Focused Phase 3 tests: 18 passed. Full Document State suite: 165 passed. No production implementation change was required.

### Objectives

- Extract a reusable repository behavior suite and run it against in-memory and SQLite bundles.
- Verify transaction rollback and consistent count/page reads.
- Verify optimistic concurrency and append idempotency with independent connections.
- Verify migration/repository privacy and safe error projection under injected failures.
- Confirm Query Facade adapter parity for both repository implementations.

### Expected Files

Create:

- `tests/document_state/test_repository_conformance.py`
- `tests/document_state/persistence/test_sqlite_transaction_consistency.py`
- `tests/document_state/persistence/test_sqlite_concurrency.py`

Modify only when verified issues require it:

- `src/document_state/persistence/sqlite/connection.py`
- `src/document_state/persistence/sqlite/repositories.py`
- `src/document_state/adapters/query_facade_adapter.py`
- existing Document State tests
- v0.12 planning/status documentation

### Tests

- In-memory and SQLite implementations satisfy identical public behavior.
- Failed writes roll back record and idempotency state together.
- Stale expected versions conflict with no lost update.
- Concurrent identical append is idempotent; conflicting reuse fails safely.
- Count and page data are consistent within one read transaction.
- Driver errors map to stable repository errors without internals.
- Adapter results preserve v0.10 mappings, privacy, filters, and ordering.

### Verification

```text
python -m pytest tests/document_state -q
python -m pytest tests/workflow_runtime/query_facade -q
python -m pytest tests/api/document_intelligence tests/ui/streamlit tests/review_runtime -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

### Stop Condition

Completed. Stop before composition selection or activation. Do not activate durable mode in API/UI.

## 5. Phase 4: Composition Root Planning And Optional Runtime Selection

**Completion note:** Added a frozen `DocumentStateComposition` result and explicit `compose_document_state()` factory for validated `in_memory` or file-backed `sqlite` selection. SQLite is imported and initialized only in its selected branch; invalid, incomplete, unavailable, and deferred backends fail without fallback. Focused Phase 4 tests: 10 passed. Full Document State suite: 175 passed. API/UI defaults and provider wiring remain unchanged.

### Objectives

- Add typed, explicit selection between `in_memory` and `sqlite` repository bundles.
- Fail closed on unknown backends, missing paths, migration mismatch, or unavailable sources.
- Keep secrets and deployment environment parsing outside repository logic.
- Prove injection into `DocumentStateQueryFacadeAdapter` without API/UI repository imports.
- Preserve current preview defaults unless owner explicitly approves durable selection.

### Expected Files

Create:

- `src/document_state/composition.py`
- `tests/document_state/test_composition.py`

Modify only if injection requires a contract-preserving seam:

- API app/provider construction modules, without endpoint or payload changes
- v0.12 planning/status documentation

### Tests

- Explicit in-memory and SQLite selection.
- Unknown/incomplete configuration fails safely with no fallback.
- SQLite path and migration failures do not leak internals.
- Repository reader injects structurally into the existing Query Facade adapter.
- API/UI contain no Document State or persistence imports.
- v0.9 paths, methods, payloads, envelopes, request IDs, and security headers remain unchanged.
- Streamlit modes remain unchanged.

### Verification

```text
python -m pytest tests/document_state -q
python -m pytest tests/workflow_runtime/query_facade tests/api/document_intelligence -q
python -m pytest tests/ui/streamlit tests/review_runtime -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

### Stop Condition

Completed. Stop before release closure. Do not switch production defaults, add endpoints, or add live writers automatically.

## 6. Phase 5: Documentation, Release Closure, And Handoff

### Objectives

- Run focused and full regression suites.
- Add summary, handoff, release notes, migration operations guidance, and recovery limitations.
- Update ADR, roadmap, technical debt, changelog, and plans accurately.
- Prepare but do not create the final tag.

### Expected Files

Create:

- `docs/architecture/DURABLE_DOCUMENT_STATE_V1_SUMMARY.md`
- `docs/architecture/DURABLE_DOCUMENT_STATE_V1_HANDOFF.md`
- `docs/releases/v0.12-durable-document-state.md`

Modify:

- both v0.12 plans
- `docs/adr/ADR-017-durable-document-state.md`
- `docs/ROADMAP.md`
- `TECHNICAL_DEBT.md`
- `CHANGELOG.md`

### Verification

```text
python -m pytest tests/document_state -q
python -m pytest tests/workflow_runtime/query_facade -q
python -m pytest tests/api/document_intelligence tests/ui/streamlit tests/review_runtime -q
python scripts/verify_boundaries.py
python -m pytest -q
git diff --check
git status --short --branch
```

### Stop Condition

Stop after documentation and verification. Do not commit, push, or tag unless explicitly instructed.

## 7. Boundary Requirements

- Existing `src/document_state` contracts and repository protocols remain the public source of truth.
- Core Document State must not import persistence engines.
- SQLite modules may import standard library plus public/package-local Document State modules only.
- Query Facade, API, UI, Streamlit, FlowSync, and competitor-price modules do not import persistence modules.
- Composition selects implementations and injects ports; consumers do not use service locators.
- No PostgreSQL/Supabase client, storage, telemetry internal, runtime implementation, external service, OCR, or LLM dependency.

## 8. Backward Compatibility Requirements

- Preserve all v0.11 repository method names, parameters, return records, filters, pagination, ordering, and safe errors.
- Preserve v0.10 Query Facade read models and adapter behavior.
- Preserve v0.9 API paths, GET methods, payload meanings, envelopes, pagination, request IDs, and security headers.
- Preserve Streamlit `local_preview` and `api_preview` behavior.
- Keep deterministic in-memory repositories available for tests and preview mode.
- Leave legacy `src/api/app.py`, root `dashboard.py`, and competitor-price modules untouched.

## 9. Risks And Mitigations

- **SQLite mistaken for production target:** label it local/dev and defer PostgreSQL deployment.
- **Migration drift:** immutable numbered files, checksums, gaps/newer-schema checks, and transactional apply.
- **Lost updates:** database compare-and-swap with exact affected-row checks.
- **Duplicate events:** unique constraints plus canonical content hash in one transaction.
- **Write contention:** bounded busy timeout and short write transactions; no production concurrency claim.
- **Schema/model drift:** explicit mappings and shared repository conformance tests.
- **Sensitive durable data:** validate before writes and reconstruct after reads; no opaque record JSON.
- **Silent fallback:** explicit backend configuration and fail-closed factory behavior.
- **Boundary erosion:** recursive import and consumer-isolation tests in every phase.

## 10. Definition Of Done

- SQLite schema/migrations and repositories cover all ten v0.11 record families.
- Existing repository protocols remain unchanged or any additive change is separately approved.
- Shared conformance passes against in-memory and SQLite implementations.
- Durability, migration, transaction, concurrency, version, idempotency, pagination, privacy, and safe-error tests pass.
- Explicit repository selection is tested with no silent fallback or API/UI import leak.
- Existing Query Facade, API, Streamlit, Review Runtime, boundary, and full regression suites pass.
- No PostgreSQL/Supabase deployment, endpoint, UI, live writer, auth, tenant, mutation, OCR, LLM, or external-service implementation is added.

## 11. Commit And Tag Strategy

Recommended commits after owner review of each phase:

1. `feat: add durable document state schema and migrations`
2. `feat: add sqlite document state repositories`
3. `test: verify durable repository conformance`
4. `feat: add document state repository selection`
5. `chore: close v0.12 durable document state`

Recommended tag after Phase 5 owner verification:

`v0.12-durable-document-state`
