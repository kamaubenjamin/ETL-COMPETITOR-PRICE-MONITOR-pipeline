# Durable Document State v1 Plan

**Milestone:** v0.12
**Status:** Phase 1 implemented; Phases 2-5 pending

## 1. Problem Statement

v0.11 established persistence-neutral Document State records, repository ports, deterministic in-memory repositories, and a read-only Workflow Query Facade adapter. That state is volatile, process-local, and unsuitable for recovery, multiple workers, or operational history across restarts.

v0.12 adds a durable database-backed implementation behind the existing repository interfaces. It must preserve v0.9 API contracts, v0.10 read models, v0.11 privacy rules, and the approved read boundary. The milestone proves durability locally with SQLite while defining PostgreSQL as the production target; it does not connect production infrastructure.

## 2. Current And Target Architecture

Current verified path:

```text
Document Intelligence API
  -> FacadeDocumentIntelligenceProvider
  -> Workflow Query Facade
  -> DocumentStateQueryFacadeAdapter
  -> Document State repositories
  -> In-memory deterministic store
```

Target selectable path:

```text
Application composition root
  -> selects in_memory or sqlite
  -> injects Document State read/write ports

Document Intelligence API
  -> FacadeDocumentIntelligenceProvider
  -> Workflow Query Facade
  -> DocumentStateQueryFacadeAdapter
  -> Document State read repositories
  -> selected durable store
```

API and Streamlit never construct, configure, or import durable repositories. The in-memory implementation remains the deterministic test/default preview source until deployment explicitly selects a durable backend.

## 3. Goals

1. Preserve all public `src/document_state` records and repository protocols.
2. Implement durable SQLite repositories for local development and integration testing.
3. Define a database-neutral logical schema covering all ten v0.11 record families.
4. Establish ordered, checksum-verified, transactional migrations.
5. Preserve optimistic versioning and append idempotency under concurrent connections.
6. Preserve deterministic filters, ordering, bounded pagination, and safe errors.
7. Define explicit repository selection without introducing API or UI repository imports.
8. Define a portable conformance suite reusable by in-memory, SQLite, and future PostgreSQL implementations.
9. Define privacy, retention, archive, backup, and recovery responsibilities at architecture level.

## 4. Non-Goals

- PostgreSQL or Supabase implementation in v0.12.
- Production database provisioning, credentials, networking, backups, or deployment.
- API endpoint, payload, method, envelope, or UI changes.
- Upload or processing writer integration.
- Authentication, authorization, tenant isolation, or row-level security.
- Mutation endpoints or command APIs.
- Raw document/blob storage.
- OCR, LLM processing, FlowSync implementation, or external services.
- Cross-service distributed transactions or a general event bus.

## 5. Storage Strategy Decision

### Phase 1: SQLite For Local And Development Durability

Use Python's standard-library `sqlite3` driver for the first durable implementation.

- No new dependency or external service is required.
- File-backed tests can prove restart durability, migrations, indexes, transactions, idempotency, and optimistic concurrency.
- SQLite is suitable for local development, demos, single-host tools, and deterministic CI integration tests.
- It is not the production scale or multi-service concurrency target.

SQLite configuration must enable foreign keys, use an explicit busy timeout, and support WAL mode for file-backed local operation. Tests may use temporary files; `:memory:` is insufficient for restart/durability verification.

### Phase 2: PostgreSQL As Production Target

PostgreSQL is the recommended production engine after v0.12 because it supports concurrent writers, transactional DDL, stronger operational tooling, row-level locking, indexing, backup/recovery, and future tenant policy. A later milestone must implement a separate adapter and PostgreSQL-specific migrations while reusing the logical schema and repository conformance suite.

### Phase 3: Supabase/Postgres As Managed Option

Supabase may host the future PostgreSQL implementation after auth, tenant isolation, row-level security, network, secret, migration, and backup policy are approved. Document State must depend on PostgreSQL semantics and its own ports, not Supabase client APIs or platform-specific tables.

## 6. Package Layout Decision

Use a dedicated persistence subpackage:

```text
src/document_state/persistence/
  __init__.py
  config.py
  errors.py
  factory.py
  migrations.py
  schema.py
  sqlite/
    __init__.py
    # connection, mappings, and repositories begin in Phase 2
  sql/                    # begins with real migration SQL in Phase 2
    sqlite/
      0001_initial.sql
tests/document_state/persistence/
  test_migrations.py
  test_sqlite_repositories.py
  test_repository_conformance.py
  test_sqlite_transactions.py
  test_composition.py
```

This layout is preferred over flat `repositories_sqlite.py` and `repositories_postgres.py` modules because connection policy, mappings, migrations, and engine-specific behavior will grow independently. A future `persistence/postgres/` sibling can be added without putting database imports in Document State core.

Core contracts, records, privacy, errors, pagination, and repository protocols must remain database-neutral. The persistence subpackage may import standard-library database facilities and public Document State contracts only.

## 7. Logical Schema

Create one table per record family plus migration metadata:

| Table | Semantics | Primary Key / Scope |
|---|---|---|
| `document_records` | Mutable current document snapshot | `document_id`, integer `version` |
| `document_lifecycle_events` | Append-only lifecycle history | `event_id`, `document_id` |
| `processing_snapshots` | Mutable stage/run snapshot | `snapshot_id`, integer `version` |
| `validation_issue_records` | Append-only validation summaries | `issue_id`, `document_id` |
| `matching_summary_records` | Append-only matching summaries | `match_id`, `document_id` |
| `review_reference_records` | Mutable review summary | `review_case_id`, integer `version` |
| `correction_summary_records` | Append-only correction lineage | `correction_id`, `review_case_id` |
| `reprocess_plan_records` | Append-only dry-run plan summary | `plan_id`, `review_case_id` |
| `workflow_run_records` | Mutable workflow snapshot | `run_id`, integer `version` |
| `audit_event_records` | Append-only safe audit history | `event_id`, scoped references |
| `schema_migrations` | Applied migration ledger | version, name, checksum, applied timestamp |

Columns should be explicit and typed rather than storing whole records as opaque JSON. Safe metadata is stored as canonical JSON text after existing allowlist validation. Database rows are mapped back through immutable record constructors before leaving the repository.

Append-only tables also store an internal `idempotency_key` and canonical `content_hash`. These are repository implementation fields and never appear in public records or Query Facade projections.

Foreign keys should protect known parent relationships where lifecycle is clear. They must not create cross-runtime ownership or require records that may legitimately arrive out of order without an explicit ingestion rule.

## 8. Migration Strategy

- Use ordered immutable migrations named `NNNN_description.sql` per engine.
- Record migration version, filename, SHA-256 checksum, and applied UTC timestamp in `schema_migrations`.
- Apply each migration transactionally and acquire an engine-appropriate migration lock.
- Refuse startup on checksum drift, duplicate versions, gaps, or a database schema newer than supported code.
- Never edit an applied migration; add a new forward migration.
- Keep destructive or lossy migrations out of automatic startup paths until backup and rollback procedures are approved.
- Provide explicit migration inspection/apply functions; production startup auto-migration remains a deployment policy decision.

Phase 1 defines immutable migration identities, ledger records, checksum/engine/sequence validation, and deterministic schema metadata. It intentionally creates no SQL or migration execution. Phase 2 begins the initial SQLite SQL migration together with connection and repository behavior.

## 9. Transaction And Consistency Rules

### Operation Scope

- Every repository method executes in an explicit transaction or consistent read scope.
- Single-record create/update/append operations are atomic.
- SQLite writes use a bounded `BEGIN IMMEDIATE` transaction to avoid ambiguous deferred-write races.
- Reads use a transaction snapshot where multiple SQL statements are needed for count plus page data.
- Connections are not shared across threads without an explicit pool/ownership policy.

### Optimistic Versioning

Mutable updates use compare-and-swap SQL:

```text
UPDATE ...
SET ..., version = expected_version + 1
WHERE stable_id = ? AND version = expected_version
```

Exactly one affected row is success. Zero rows trigger a follow-up existence check inside the transaction to map safely to `not_found` or `conflict`. The supplied record version must equal `expected_version + 1`.

### Append Idempotency

Append-only writes atomically insert the record and its idempotency identity. Repeating the same key, stable record ID, and canonical content returns the existing immutable record. Reusing a key or stable ID with different content returns safe `conflict`. Unique constraints are the final concurrency guard; application prechecks are not sufficient.

### Cross-Record Consistency

v0.12 guarantees one repository operation at a time. Multi-record units of work, transactional workflow checkpoints, outbox delivery, and cross-query snapshot tokens remain deferred. Repository callers must not infer global snapshot consistency from independently paged collections.

## 10. Indexing And Pagination

- Preserve v0.11 bounded limit/offset contracts and deterministic tie-breakers.
- Add composite indexes matching every supported filter plus declared ordering fields.
- Include stable record IDs as final index/order tie-breakers.
- Use a transaction-consistent `COUNT(*)` and page query for `PageResult.total`.
- Reject limits/offsets before SQL execution using existing contracts.
- Avoid arbitrary sort columns and raw SQL fragments from callers.
- Document query plans for representative list operations in conformance tests.

Cursor/keyset pagination is deferred until API and Query Facade contracts are versioned for it. Large-offset performance is an accepted v0.12 limitation.

## 11. Privacy-Safe Durable Storage

- Revalidate all records through existing constructors before writes and after reads.
- Store no raw document bytes/text/pages, source rows, correction old/new values, artifact payloads, stack traces, storage paths, credentials, or unrestricted metadata.
- Store safe validation messages and summary identifiers only.
- Serialize metadata deterministically with sorted keys and bounded scalar values.
- Map driver and SQL exceptions to repository-safe codes without query text, paths, connection details, values, or stack traces.
- Keep database files, connection strings, and migration internals out of records and API projections.
- A future raw blob store is a separate encrypted, access-controlled boundary referenced by opaque ID only.

## 12. Retention And Archive Strategy

v0.12 defines policy hooks but does not delete or archive production data.

- Mutable current snapshots remain while their owning document/workflow exists.
- Lifecycle, validation, matching, correction, reprocess, and audit records require explicit retention classes before deletion.
- Legal hold must override retention.
- Archive exports must preserve lineage, checksums, timestamps, and privacy classification.
- Purge operations require authorization, audit, bounded batches, referential checks, and recovery policy.
- SQLite local/dev files are disposable unless explicitly backed up; production retention and backup targets belong to the PostgreSQL deployment milestone.

## 13. Composition Model

Repository selection is explicit and validated:

- `in_memory`: deterministic tests and preview mode.
- `sqlite`: local/dev durable mode with an explicit path and migration state.
- Unknown or incomplete configuration fails closed with a safe configuration error; there is no silent fallback.

`src/document_state/persistence/factory.py` may construct a repository bundle from a typed configuration object. It must not read API requests or own deployment secrets. A top-level application bootstrap, outside API/UI packages, later injects the selected read port into `DocumentStateQueryFacadeAdapter` and supplies write ports to approved producers.

Phase 4 may prove selection and injection in tests. Switching the default API source or adding live writers requires separate owner approval and must preserve the rule that API and Streamlit do not import Document State.

## 14. Workflow Query Facade Integration

No Query Facade or API contract changes are required. `DocumentStateQueryFacadeAdapter` accepts the selected `DocumentStateReadRepositories` implementation and continues to own projection, facade pagination, and safe error translation.

The approved read direction remains:

```text
API / Streamlit
  -> Document Intelligence API
  -> FacadeDocumentIntelligenceProvider
  -> Workflow Query Facade
  -> DocumentStateQueryFacadeAdapter
  -> injected Document State read repositories
```

## 15. Testing Strategy

- Run the same repository conformance suite against in-memory and SQLite implementations.
- Use temporary file databases for durability/reopen, migration, and multi-connection tests.
- Verify all ten record families, filters, orderings, pagination bounds, and empty/missing behavior.
- Verify optimistic conflicts with independent connections and no lost updates.
- Verify append idempotency and conflicting concurrent keys/IDs.
- Verify transaction rollback under injected failures.
- Verify migration application, replay, checksum drift, gaps, and unsupported newer schemas.
- Verify privacy rejection before SQL and safe error mapping after driver failures.
- Verify no mutable state, connection, SQL, file path, or idempotency hash escapes public ports.
- Preserve Query Facade, API, Streamlit, Review Runtime, boundary, and full-regression suites.
- PostgreSQL conformance is deferred but the suite must remain engine-neutral.

## 16. Runtime Boundary Rules

- Core Document State remains standard-library/package-local and database-neutral.
- Engine modules stay under `src/document_state/persistence/` and implement existing ports.
- API, Streamlit, and Query Facade do not import persistence modules.
- The Query Facade adapter imports only public Document State and public Workflow Query Facade boundaries.
- Composition is explicit and outside consumer packages.
- No competitor-price storage, legacy `src/storage`, telemetry internals, runtime implementations, external services, OCR, or LLM imports.

## 17. Risks And Open Questions

- **SQLite write contention:** acceptable for local/dev; use bounded transactions and do not claim production concurrency.
- **SQLite/PostgreSQL drift:** keep logical schema and conformance behavior shared while allowing engine-specific migrations.
- **Migration safety:** checksum immutable migrations and fail closed on drift/newer schemas.
- **Count plus page consistency:** use one read transaction; cross-endpoint snapshots remain unresolved.
- **Metadata querying:** metadata is not an arbitrary query surface; promote required filters to explicit columns.
- **Foreign-key arrival order:** define parent requirements per record family before enabling strict relationships.
- **Retention obligations:** legal, regional, and customer requirements are not yet defined.
- **Composition ownership:** the final process bootstrap package and deployment configuration source need owner approval.
- **Production PostgreSQL driver:** dependency and pooling choice remain deferred.

## 18. Definition Of Done

- Existing v0.11 public contracts and repository protocols remain compatible.
- Initial SQLite schema and migrations cover all ten record families.
- SQLite repositories pass the shared conformance, transaction, version, idempotency, privacy, and durability tests.
- Repository selection is explicit, tested, and has no silent fallback.
- API/UI do not import repositories and v0.9/v0.10 behavior remains unchanged.
- No PostgreSQL/Supabase service, auth, tenant implementation, endpoint, UI, upload, OCR, LLM, or external service is added.
- Documentation distinguishes local/dev durability from production readiness.

## 19. Release Readiness Criteria

- Focused persistence, Document State, Query Facade, API, UI, Review Runtime, boundary, and full regression suites pass.
- Migration replay and checksum verification pass from a blank temporary database.
- File reopen proves durable records and deterministic reads.
- Concurrent version and idempotency tests pass without sleeps or network services.
- No generated database file is committed.
- Summary, handoff, release notes, roadmap, debt, changelog, and ADR are complete.
- Recommended tag is prepared but not created by Codex.
