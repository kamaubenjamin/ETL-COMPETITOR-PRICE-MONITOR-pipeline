# ADR-017: Durable Document State v1

## Status

Accepted; Phases 1-4 implemented and Phase 5 pending.

## Context

v0.11 introduced immutable Document State records, privacy validation, bounded pagination, repository-safe errors, separate read/write repository protocols, deterministic in-memory repositories, and a read-only Workflow Query Facade adapter. The in-memory implementation proves behavior but loses state at process exit and cannot serve as operational persistence.

The durable implementation must preserve existing public contracts and privacy boundaries, provide deterministic local verification without production infrastructure, and establish a path toward a production relational database.

## Decision

Adopt a phased relational storage strategy:

1. Implement SQLite with Python's standard-library `sqlite3` for v0.12 local/dev durability and CI verification.
2. Treat PostgreSQL as the production target for a later implementation milestone.
3. Treat Supabase as a possible future managed PostgreSQL deployment, not as a domain dependency.

Place engine-specific code under:

```text
src/document_state/persistence/
```

Core Document State contracts and repository protocols remain persistence-neutral. The SQLite implementation must satisfy the existing ports without changing API or Query Facade contracts.

## Storage Option Rationale

### SQLite

Selected for v0.12 because it is durable, local, deterministic, dependency-free, and testable with temporary files. It can prove schema migration, transaction, indexing, version, idempotency, reopen, and recovery behavior. It is not approved as the production concurrency target.

### PostgreSQL

Selected as the production target because it provides robust concurrent transactions, locking, indexing, backup/recovery, observability, and a future route to tenant-aware policy. Driver, pooling, deployment, schema dialect, and operational ownership remain deferred.

### Supabase/Postgres

Retained as a future managed option after PostgreSQL repository behavior, auth, tenant isolation, row-level security, secret management, and deployment policy are approved. Repository code must not use Supabase-specific clients or couple domain contracts to managed-platform features.

## Package Decision

A persistence subpackage is preferred over flat engine files:

```text
src/document_state/persistence/
  config.py
  errors.py
  factory.py
  migrations.py
  schema.py
  sqlite/
    connection.py
    migrations.py
    mappers.py
    repositories.py
    schema.sql
```

This keeps database concerns out of core contracts, gives migrations and mappings explicit ownership, and permits a future `postgres/` sibling with separate engine policy.

## Schema Decision

- Use explicit relational tables and columns for all ten v0.11 record families.
- Do not store complete records as opaque JSON documents.
- Store safe allowlisted metadata only as canonical JSON text.
- Keep mutable current snapshots versioned.
- Keep lifecycle, validation, matching, correction, reprocess, and audit records append-only.
- Store idempotency keys and canonical content hashes as private repository columns.
- Add indexes matching approved filters and deterministic ordering.
- Keep raw documents, rows, correction values, artifacts, stack traces, storage details, and credentials outside query-facing tables.

## Migration Decision

- Use ordered immutable engine-specific SQL migrations.
- Track version, filename, checksum, and applied timestamp.
- Apply migrations transactionally with engine-appropriate locking.
- Fail closed on checksum drift, gaps, duplicate versions, or unsupported newer schemas.
- Never modify an applied migration; add a forward migration.
- Keep production auto-migration policy deferred to deployment architecture.

## Transaction Decision

- One repository operation is one atomic transaction/consistent read scope.
- SQLite writes use short bounded `BEGIN IMMEDIATE` transactions.
- Mutable updates use `WHERE id = ? AND version = expected_version`; zero affected rows map safely to `not_found` or `conflict`.
- Append records and idempotency identity commit together under unique constraints.
- Identical retry returns the existing record; conflicting key/ID reuse returns safe `conflict`.
- Multi-record units of work, outbox delivery, and cross-endpoint snapshots remain deferred.

## Composition Decision

Repository selection is explicit between `in_memory` and `sqlite`, with no silent fallback. A persistence factory may create repository bundles from typed configuration, but API and UI do not import that factory. A top-level application composition root later injects the read port into `DocumentStateQueryFacadeAdapter` and supplies write ports to approved producers.

The read boundary remains:

```text
API / Streamlit
  -> Document Intelligence API
  -> FacadeDocumentIntelligenceProvider
  -> Workflow Query Facade
  -> DocumentStateQueryFacadeAdapter
  -> selected Document State read repositories
```

## Privacy And Retention Decision

Existing v0.11 privacy validators apply before durable writes and after reads. Driver errors are translated to safe repository codes without SQL, values, paths, connection details, or stack traces. Retention and archive are policy hooks only in v0.12; no production purge occurs until legal hold, authorization, audit, backup, and recovery rules are approved. Raw encrypted blob storage remains a separate future boundary.

## Consequences

### Positive

- Durable behavior can be verified locally without a service or new dependency.
- Existing repository consumers remain unchanged.
- Schema, migration, transaction, and idempotency behavior become explicit.
- A shared conformance suite reduces drift between in-memory, SQLite, and future PostgreSQL implementations.
- API/UI boundaries remain intact.

### Negative

- SQLite and PostgreSQL require separate engine-specific migrations and concurrency policy.
- SQLite does not prove production-scale concurrent behavior.
- Limit/offset pagination remains inefficient at large offsets.
- Production composition, live writers, tenant policy, and operational ownership remain unresolved.

## Deferred Decisions

- PostgreSQL driver, pooling, deployment, and migration implementation.
- Supabase project, row-level security, and managed backup policy.
- Production composition-root package and configuration/secret source.
- Cross-record transaction/unit-of-work and outbox contracts.
- Tenant partitioning, auth/authz, retention periods, archive target, backup/recovery objectives, and telemetry.
- Mutation endpoints, upload processing, encrypted raw blob storage, FlowSync Document Intelligence, OCR, LLM, and external services.

## Compatibility

ADR-017 is additive to ADR-016. It preserves v0.11 repository interfaces, v0.10 Query Facade read models, and v0.9 API paths, GET-only methods, payload meanings, envelopes, request IDs, pagination, and security headers. It does not modify Streamlit, legacy API/dashboard, or competitor-price modules.

## Implementation Status

Phase 2 implements the decision with file-backed standard-library SQLite, one short-lived connection per operation, `BEGIN IMMEDIATE` writes, transaction-consistent count/page reads, explicit relational columns, canonical safe metadata JSON, and an ordered checksum-verified migration ledger. Phase 3 verifies the same public repository contract against in-memory and SQLite implementations and proves reopen durability, migration replay, rollback, read-snapshot consistency, single-winner compare-and-swap, identical append retries, and conflicting idempotency behavior with deterministic short-lived tests. Phase 4 adds explicit validated selection through a frozen composition result, with no fallback and no automatic API/UI wiring. SQLite remains local/dev infrastructure; release closure remains in Phase 5.
