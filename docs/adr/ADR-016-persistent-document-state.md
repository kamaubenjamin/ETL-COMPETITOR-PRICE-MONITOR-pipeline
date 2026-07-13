# ADR-016: Persistent Document State v1

## Status

Accepted; Phase 1 implemented and Phases 2-5 pending.

## Context

The v0.9 Document Intelligence API and v0.10 Workflow Query Facade provide a stable, privacy-safe read path, but all current records are deterministic preview fixtures. Future ingestion, processing, validation, matching, review, workflow, and audit activity needs an operational state boundary without allowing API/UI consumers to import runtime or persistence implementations.

The persistence domain must remain independent of database technology, avoid legacy competitor-price storage, and preserve existing API and Query Facade contracts.

## Decision

Create a persistence-neutral Document State domain at:

```text
src/document_state/
```

It owns immutable safe records, bounded repository pagination, stable repository errors, explicit read/write ports, and deterministic in-memory repository implementations for v0.11.

Document State is the future operational source for:

- Document records and lifecycle history.
- Processing status snapshots.
- Validation issue records.
- Matching result summaries.
- Review case references and summaries.
- Correction history summaries without raw values.
- Declarative reprocess plan summaries.
- Workflow run records.
- Audit event records.

## Package Location Rationale

`src/document_state/` is selected because document operational state is a platform domain shared by future producers and read consumers. It is not owned solely by Workflow Runtime and is not a generic storage implementation.

`src/workflow_runtime/document_state/` is rejected because it makes Workflow the owner of records written by document, validation, matching, and review capabilities. `src/storage/document_state/` is rejected because storage technology should not own domain contracts and the existing storage package contains unrelated legacy concerns.

## Repository Decision

- Use explicit repository ports for each record family, not generic CRUD.
- Separate read protocols from write protocols.
- Use immutable append-only records for lifecycle, corrections, reprocess plans, and audit.
- Use optimistic integer versions for mutable current-state snapshots.
- Require stable IDs for append idempotency and conflict detection.
- Define bounded pagination and deterministic ordering independent of database technology.
- Limit atomicity claims to one repository operation in v0.11.
- Defer database transactions, isolation, outbox, and cross-repository consistency.

## Query Facade Integration Decision

An explicit adapter under `src/document_state/adapters/` may implement public Workflow Query Facade ports. The adapter maps public Document State read records into existing v0.10 immutable read models.

Dependency direction is enforced as follows:

- Core Document State does not import Workflow Query Facade.
- Query Facade does not import Document State.
- Only the explicit adapter imports both public contract surfaces.
- API and UI do not import Document State.
- Production composition and source selection remain deferred.

This preserves the read path:

```text
API -> FacadeDocumentIntelligenceProvider -> Workflow Query Facade Port
    -> injected Document State adapter -> Document State read repositories
```

## Privacy Decision

- Query-facing repositories do not store raw document content, rows, or artifact payloads.
- Correction summaries never store raw old/new values.
- Persisted public errors never include exception text or stack traces.
- Validation and matching records store safe summaries, not source values or full master records.
- Audit metadata is scalar, bounded, allowlisted, and size-limited.
- Any future raw blob store is a separate encrypted, access-controlled boundary referenced by opaque ID.

## API Compatibility Decision

v0.11 does not change v0.9 API paths, methods, payload meanings, envelopes, request IDs, pagination, or security headers. It does not change v0.10 Query Facade read models or make API/Streamlit repository consumers.

## Consequences

### Positive

- Persistence ownership becomes explicit and testable.
- Database choice can change without changing API or Query Facade contracts.
- Future producers have narrow write boundaries with concurrency and idempotency semantics.
- Privacy rules are enforced before durable storage is introduced.
- Deterministic repositories allow behavior to be verified without infrastructure.

### Costs And Risks

- Document State and Query Facade maintain separate models and require explicit mapping.
- In-memory behavior cannot prove database isolation or durability.
- Production composition, tenant policy, and cross-source consistency remain unresolved.
- Additional ports can become verbose if record boundaries are not kept focused.

## Rejected Alternatives

### API Reads Repositories Directly

Rejected because it bypasses the Workflow Query Facade and couples HTTP contracts to persistence.

### Streamlit Reads Repositories Directly

Rejected because UI consumers must use the API and must not own backend state.

### Query Facade Imports Concrete Repositories

Rejected because it violates the v0.10 dependency rule and hides composition inside the read boundary.

### Generic Repository Or Service Locator

Rejected because generic CRUD and dynamic lookup obscure privacy, ordering, concurrency, and ownership semantics.

### Database And Migrations In Phase 1

Rejected because engine choice, schema lifecycle, tenant policy, encryption, backup, retention, and operations are not approved.

### Reuse Legacy Storage Files

Rejected because legacy JSON/CSV state belongs to separate competitor-price workflows and does not provide the required contracts or guarantees.

## Deferred Decisions

- Database engine, schema, migrations, ORM/query tooling, and connection lifecycle.
- Production composition root and live producer adapters.
- Transactions, isolation, outbox/event delivery, backup, retention, and disaster recovery.
- Authentication, authorization, tenant partitioning, encryption/key management, and policy filtering.
- Caching, indexing, cursor pagination, archival, telemetry, and service-level objectives.
- Mutation APIs, upload processing, FlowSync Document Intelligence, OCR, LLM, and external services.

## Implementation Direction

Implement the five phases in `docs/architecture/PERSISTENT_DOCUMENT_STATE_V1_IMPLEMENTATION_PLAN.md`. Stop each phase independently. Do not introduce database, migration, API/UI, live writer, auth, mutation endpoint, or external-service work without a separately approved decision.
