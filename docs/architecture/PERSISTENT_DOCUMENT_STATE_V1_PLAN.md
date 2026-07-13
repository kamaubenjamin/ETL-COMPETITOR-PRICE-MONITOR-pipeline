# Persistent Document State v1 Plan

**Milestone:** v0.11
**Status:** Phase 1 implemented; Phases 2-5 pending

## 1. Problem Statement

The Document Intelligence API currently reads deterministic preview data through the Workflow Query Facade. The platform has no repository-owned operational state for document lifecycle, processing outcomes, validation issues, matching summaries, review references, workflow runs, or audit history. Connecting future ingestion and processing directly to API providers would bypass the v0.10 boundary and spread persistence concerns across runtimes.

v0.11 defines a persistence-neutral document state domain and repository layer. It proves the contracts with deterministic in-memory repositories and a Query Facade adapter, while deferring database selection, migrations, live writers, and production composition.

## 2. Goals

1. Establish persistent document state as the future operational source for Document Intelligence read models.
2. Define immutable, JSON-compatible persistence contracts and narrow repository ports.
3. Separate mutable snapshots from append-only history and audit records.
4. Preserve deterministic ordering, bounded reads, optimistic concurrency, and idempotent record identity.
5. Keep the Workflow Query Facade as the only approved API read boundary.
6. Prove repository behavior with deterministic in-memory implementations.
7. Define an injected adapter from repositories to public Query Facade read models.
8. Enforce privacy-safe storage and projection boundaries.

## 3. Non-Goals

- Database engine selection, schema migrations, ORM adoption, or deployment.
- File-backed production persistence or reuse of legacy JSON storage.
- API or UI changes, upload processing, or live runtime writers.
- Authentication, authorization, tenant isolation, or policy filtering.
- Mutation endpoints or command APIs.
- Raw document/blob storage, OCR, LLM processing, or external services.
- Competitor-price persistence or migration.

## 4. Package Location Decision

Selected location:

```text
src/document_state/
```

| Candidate | Decision |
|---|---|
| `src/document_state/` | Selected. Gives operational document state explicit platform ownership and keeps it independent of API, Workflow implementation, and generic storage utilities. |
| `src/workflow_runtime/document_state/` | Rejected. Persistence will serve future ingestion, processing, review, and workflow writers; Workflow should consume it through ports rather than own every record. |
| `src/storage/document_state/` | Rejected. `storage` is an implementation concern and risks mixing legacy files, database details, and domain contracts. |

The core package must use only the standard library and its own modules. A dedicated `src/document_state/adapters/` module may depend on public Workflow Query Facade contracts to implement its consumer port; core contracts and repositories must not.

## 5. Target Architecture

```text
Future ingestion / processing / review / workflow writers
                         |
                         v
             Document State write ports
                         |
                         v
        Repository implementation (in-memory in v0.11)
                         |
                         v
               Document State read ports
                         |
                         v
      Repository-to-Query-Facade source adapter
                         |
                         v
              Workflow Query Facade Port
                         |
                         v
        FacadeDocumentIntelligenceProvider
                         |
                         v
             Document Intelligence API
```

The API and Streamlit never receive repository objects. v0.11 proves adapter compatibility through explicit test composition; production source selection remains deferred until identity, tenant, persistence, and deployment decisions exist.

## 6. State Contracts

Contracts use frozen standard-library dataclasses or equivalent immutable records. Timestamps are timezone-aware UTC ISO-8601 strings. IDs are bounded opaque strings. All serialization is deterministic and JSON-compatible.

Common record rules:

- Stable record ID and relevant `document_id`, `workflow_run_id`, or `review_case_id` references.
- `created_at`; mutable snapshots also include `updated_at` and integer `version`.
- Bounded source runtime/stage identifiers and correlation identifiers where required.
- No arbitrary object values, callbacks, storage handles, or implementation metadata.
- Repository error codes: `invalid_record`, `invalid_query`, `not_found`, `conflict`, `source_unavailable`, and `internal_error`.

## 7. Repository Boundaries

Repository ports are explicit rather than generic CRUD abstractions.

| Boundary | Record Semantics | Required Operations |
|---|---|---|
| Document records | Versioned current snapshot | create, get, list, update with expected version |
| Lifecycle history | Append-only | append event, list by document |
| Processing status | Versioned stage/attempt snapshot | create/update with expected version, list by document/run |
| Validation issues | Immutable per validation execution | idempotent append, get/list |
| Matching summaries | Immutable per matching execution | idempotent append, get/list |
| Review case references | Versioned safe summary | put with expected version, get/list |
| Correction history | Append-only safe summary | append, list by review case; never store raw old/new values |
| Reprocess plans | Append-only declarative summary | append, list by review case |
| Workflow runs | Versioned run snapshot | create, get/list, update with expected version |
| Audit events | Append-only | append, list by allowed scope/type |

Read and write protocols are separate so query adapters receive no mutation surface. Repeated append of the same stable ID is deterministic: identical content is idempotent; conflicting content raises `duplicate`. Versioned updates require `expected_version` and return a new immutable record.

## 8. Ordering And Pagination

Document State defines persistence-neutral bounded page requests/results rather than importing Query Facade pagination contracts. The adapter translates between the two.

- Default and maximum limits are fixed constants.
- Offset is non-negative; cursor pagination remains deferred.
- Every list operation declares stable ordering and an ID tie-breaker.
- Repositories return immutable tuples, not mutable internal collections.
- Invalid filters, ordering, limits, or offsets fail before repository state changes.

## 9. Privacy-Safe Persistence

- Read-model repositories never store raw document bytes, text, pages, rows, or extracted artifact payloads.
- Correction history stores field path, operation, reason, actor reference, lineage, and timestamps, but no raw old/new values.
- Persisted public errors contain safe code, stage/source reference, and bounded message code only; no exception text or stack trace.
- Audit metadata is scalar, bounded, allowlisted, and size-limited.
- Matching records contain candidate identifiers and confidence/status summaries, not full master records.
- Validation records contain field/rule/code/severity and safe messages, not source values or rows.
- Repository serialization rejects unknown unsafe metadata keys and non-JSON values.
- Raw source/blob storage, if later required, must be a separate encrypted access-controlled boundary referenced only by opaque artifact ID.

## 10. Write Model And Future Producers

Future runtimes will write through narrow document-state services or write ports, never repository implementation imports. Each write supplies stable IDs, source lineage, correlation ID, timestamp, and expected version where applicable. Producers remain owners of business decisions; Document State validates storage contracts, concurrency, idempotency, and privacy but does not decide workflow, matching, validation, or review outcomes.

Cross-record transactions and outbox/event publication require database-specific design and remain deferred. Until then, v0.11 tests atomicity only within one repository operation.

## 11. Workflow Query Facade Integration

Phase 3 adds a repository-backed adapter under `src/document_state/adapters/` that:

- Implements the public `WorkflowQueryFacadePort` or its narrow public source ports.
- Depends only on public Query Facade contracts/read models and public Document State read ports.
- Maps repository records explicitly into existing immutable v0.10 read models.
- Translates pagination, filters, ordering, not-found, unavailable, and internal errors safely.
- Exposes no write repository or mutation method.
- Preserves v0.9 API payload meanings through existing `FacadeDocumentIntelligenceProvider` parity tests.

The Query Facade package does not import Document State. API and UI packages do not import Document State. Production composition remains outside those packages and is deferred.

## 12. Runtime Boundary Rules

- `src/document_state/` core: standard library and own modules only.
- Repository implementations: core Document State public contracts only; no API/UI/runtime/telemetry/competitor dependencies.
- Query adapter: public Document State read ports plus public Workflow Query Facade exports only.
- Query Facade: no Document State or repository implementation imports.
- API/Streamlit: no Document State imports.
- Future writer adapters may depend on public Document State write ports, never concrete repositories.
- No new boundary-verifier exemption is acceptable by default.

## 13. Concurrency And Consistency

- Mutable snapshots use optimistic integer versions.
- In-memory repositories use a lock around each atomic operation and never expose internal mutable collections.
- Append-only records use stable IDs for idempotency and conflict detection.
- Ordering is deterministic after concurrent writes.
- Cross-repository snapshot consistency, transactions, isolation levels, and distributed locking are deferred to the database architecture.

## 14. Testing Strategy

- Contract immutability, validation, JSON serialization, and unsafe-field rejection.
- Repository protocol structure and absence of generic/mutation leakage into read ports.
- Deterministic create/get/list/update/append behavior.
- Optimistic version conflict and append idempotency.
- Defensive copies/immutable returns and concurrent access.
- Bounded pagination, filtering, ordering, and tie-breakers.
- Adapter parity with v0.10 read models and v0.9 API provider shapes.
- Safe not-found, invalid, unavailable, and internal error translation.
- Recursive forbidden-import, privacy-key, and no-raw-payload scans.
- Existing API, Streamlit, Review Runtime, Query Facade, boundary, and full regression suites.

## 15. Risks And Mitigations

| Risk | Mitigation |
|---|---|
| Domain package becomes a generic data lake | Keep explicit record types and repository ports; prohibit artifact payloads. |
| Duplicate models drift from Query Facade | Explicit adapter mapping and parity tests; no shared mutable dictionaries. |
| In-memory semantics imply database guarantees | Document operation-level guarantees only; defer transactions and isolation. |
| Persistence leaks sensitive values | Contract allowlists, metadata bounds, negative privacy tests, separate future blob boundary. |
| Repositories become business services | Producers own decisions; repositories enforce storage contracts only. |
| Cross-runtime coupling moves into adapters | Restrict adapter imports to public ports and verify recursively. |

## 16. Definition Of Done

- ADR-016 and both v0.11 plans are approved.
- Persistence-neutral immutable contracts and explicit read/write ports exist under `src/document_state/`.
- Deterministic in-memory repositories satisfy contract, pagination, idempotency, and concurrency tests.
- A read-only repository adapter satisfies public Workflow Query Facade ports without reverse imports.
- Existing v0.9 API contracts and v0.10 read models remain unchanged.
- Privacy and boundary verification passes with no new exemptions.
- Focused and full regression suites pass.
- Summary, handoff, release notes, roadmap, debt, and changelog close the milestone.

## 17. Deferred Work

- Database selection, schemas, migrations, ORM/query builder, and connection management.
- Production composition root and live runtime writer adapters.
- Cross-repository transactions, isolation, outbox/event delivery, backups, retention, and disaster recovery.
- Tenant partitioning, row-level policy, encryption/key management, auth/authz, and data-subject lifecycle.
- Caching, cursor pagination, high-volume indexing, archival, and service-level objectives.
- Mutation APIs, uploads, OCR, LLM, external services, and FlowSync Document Intelligence.
