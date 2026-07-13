# ADR-015: Workflow Query Facade v1

## Status

Accepted; Phase 1 implemented and later phases pending.

## Context

v0.9 established a separate read-only Document Intelligence API and optional Streamlit API preview. Its deterministic provider proves transport contracts but does not expose live platform state. R05 prevents API Runtime from importing Document, Entity, Transform, Matching, Review, storage, telemetry, UI, or competitor-price internals.

Live read composition therefore needs a public boundary owned by a runtime the API is permitted to consume. That boundary must not solve the dependency problem by collecting direct imports from every runtime.

## Decision

Create Workflow Query Facade v1 at:

```text
src/workflow_runtime/query_facade/
```

The facade is read-only and publishes strict JSON-compatible read models, filters, pagination contracts, errors, source protocols, and explicit query methods for Document Intelligence projections.

Workflow Runtime owns the public orchestration-level query surface. Source runtimes continue to own their state and future read adapters. API Runtime owns HTTP validation, envelopes, request IDs, security headers, and error status mapping. UI consumers continue to use the API.

## Package Location Rationale

`src/workflow_runtime/query_facade/` is selected because R05 already permits API-to-Workflow dependency and Workflow owns orchestration-level execution state. The location makes ownership visible and keeps the facade out of API and UI packages.

`src/query_facade/` is rejected because it has no clear owner and invites unrelated cross-runtime aggregation. `src/document_intelligence/query_facade/` is rejected because it creates an implicit new runtime and weakens the established API-to-Workflow boundary.

## Dependency Decision

- Facade contracts and service do not import runtime implementation modules.
- Narrow read-only source protocols are injected explicitly.
- No dynamic discovery, plugin loading, service locator, or generic repository is introduced.
- Future runtime-owned adapters implement the ports through approved public read services.
- Adapter composition requires an explicit boundary; no new verifier exemption is allowed.
- API code may import only the facade's documented public exports, not its implementation internals.

## Contract Decision

The facade defines explicit read models for:

- Document inbox and detail projections.
- Processing status.
- Validation issues.
- Matching results.
- Review case summaries.
- Correction history summaries without controlled values.
- Reprocess plan summaries without artifact payloads.
- Workflow run summaries.
- Audit event summaries with allowlisted metadata.

Collections use bounded limit/offset pagination compatible with v0.9 and documented deterministic total ordering. Query methods are explicit; there is no arbitrary query language or field selection.

## API Compatibility Decision

The v0.9 API paths, GET-only methods, filters, response envelopes, pagination metadata, payload meanings, request IDs, errors, security headers, and CORS policy remain unchanged. An API-side provider translates facade contracts into the existing provider interface.

The deterministic API provider remains available during migration. Provider selection is explicit, and unavailable facade mode must not silently return preview data.

## Privacy And Security Decision

- No raw documents, rows, correction values, comments, credentials, arbitrary metadata, exceptions, or stack traces cross the facade.
- Metadata and errors are bounded and allowlisted.
- The facade performs read projection, not authentication or authorization.
- Production live reads remain blocked until identity, tenant, and policy enforcement are designed.

## Consequences

### Benefits

- Preserves R05 while giving the API one stable live-read direction.
- Centralizes deterministic query and privacy semantics without moving source ownership.
- Keeps API contracts and runtime query contracts independently testable.
- Supports Streamlit and future FlowSync through unchanged HTTP contracts.

### Tradeoffs

- v0.10 still uses deterministic in-memory sources and does not deliver live operational data.
- Facade and API models require explicit translation and parity tests.
- Cross-source transactional snapshot consistency remains unresolved until durable source architecture exists.
- A future composition boundary is required to inject real adapters safely.

## Rejected Alternatives

### API Imports Runtime Services Directly

Rejected because it violates R05 and spreads privacy/query composition across routers.

### Facade Imports Every Runtime Internally

Rejected because it merely relocates forbidden coupling and creates a dumping ground.

### Generic Top-Level Query Package

Rejected because ownership and product scope become ambiguous.

### Database Read Model In v0.10

Rejected because persistence, migrations, consistency, retention, and tenant policy are not approved.

### Mutation Commands In The Facade

Rejected because commands require separate identity, authorization, idempotency, concurrency, transaction, and audit design.

## Deferred Decisions

- Live runtime adapters and their composition root.
- Database/materialized projections, caching, cursor pagination, and consistency guarantees.
- Authentication, authorization, tenant isolation, rate limiting, gateway, TLS, and production CORS.
- Mutation commands and workflow execution.
- Production telemetry and service-level objectives.
- FlowSync Document Intelligence, OCR, LLM processing, and external services.

## Follow-Up

Implement the five phases in `docs/architecture/WORKFLOW_QUERY_FACADE_V1_IMPLEMENTATION_PLAN.md`. Do not connect live runtime sources or add mutation behavior without a separately approved boundary and security decision.

Phase 1 implements only dependency-free contracts, pagination, read models, safe errors, and structural read ports. Deterministic providers and query services remain Phase 2 work.
