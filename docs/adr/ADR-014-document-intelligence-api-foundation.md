# ADR-014: Document Intelligence API Foundation v1

## Status

Accepted; Phase 1 implemented and later phases pending.

## Context

Document Intelligence backend runtimes and the internal Streamlit console now exist, but future clients need a stable transport boundary. The current `src/api/app.py` serves the legacy FlowSync ETL/Competitor Price execution plane and carries temporary boundary exemptions. Extending it directly would couple product surfaces, inherit mutation and telemetry concerns, and risk violating R05, which limits API Runtime dependencies to Workflow Runtime and shared utilities.

Streamlit and a future FlowSync Document Intelligence application must consume backend-owned state without importing runtime internals or becoming sources of truth. Authentication, authorization, persistence, mutation contracts, and public deployment are not ready for v0.9.

## Decision

Create a separate versioned **Document Intelligence API** application under `src/api/document_intelligence/` with base path `/api/v1/document-intelligence`.

v0.9 exposes read-only endpoints for health, document inbox, processing, validation, matching, review cases, correction history, reprocess plans, workflow runs, and audit logs. It starts with deterministic providers and strict consumer-neutral JSON contracts.

The API owns transport concerns only: routing, request/query validation, versioning, response envelopes, pagination, safe errors, OpenAPI, and transport limits. Backend runtimes remain authoritative for artifacts, execution, validation, matching, review decisions, corrections, reprocess intent, and audit.

## Runtime Boundary Decision

R05 remains binding. Document Intelligence API modules must not directly import Document, Entity, Transform, Matching, Review, storage, telemetry, UI, or competitor-price internals.

Deterministic v0.9 providers may be API-owned fixtures. A future live provider must consume a public Workflow Runtime query facade that aggregates approved runtime projections. The API must not introduce a new boundary exemption to obtain live data.

This ADR refines ADR-007 and does not replace it. ADR-007 remains the general API Runtime ownership decision; ADR-014 establishes the separate read-only Document Intelligence product surface and its stricter v0.9 scope.

## Consumer Decision

- Streamlit uses an API-backed provider adapter while retaining explicit deterministic local mode.
- Future FlowSync Document Intelligence uses the same HTTP contracts as an independent client.
- Neither client owns runtime rules, review transitions, corrections, workflow execution, or audit truth.
- Existing FlowSync Competitor Price and root `dashboard.py` remain separate and unchanged.

## Read-Only Decision

No ingestion, upload, correction, decision, reprocess, workflow-run, or other mutation endpoint is included. Unsupported mutation methods are absent and explicitly tested.

Mutation APIs require a future ADR covering trusted identity, authorization policy, idempotency, optimistic concurrency, audit, CSRF/CORS, rate limits, and durable transactional behavior.

## Contract Decision

- Explicit major version in the path.
- JSON-compatible consumer-neutral records.
- Stable deterministic ordering and bounded limit/offset pagination.
- Structured privacy-safe errors with request IDs.
- Correction history excludes controlled values and raw originals.
- Audit, validation, and matching responses expose bounded summaries only.
- OpenAPI is verified as a release contract.

## Security Decision

v0.9 is not an authenticated or publicly deployable API. CORS is denied by default, no wildcard origin is configured, and health output excludes sensitive dependency details. Authentication, authorization, TLS termination, API gateway, rate limiting, tenant isolation, and production exposure are deferred.

## Consequences

### Benefits

- One stable read contract for internal Streamlit and future FlowSync Document Intelligence.
- Clear separation from competitor-price API and UI concerns.
- Backend runtimes remain authoritative and independently testable.
- Read-only scope permits contract, privacy, and boundary hardening before mutation risk.
- Deterministic providers make local and CI verification hermetic.

### Tradeoffs

- v0.9 does not expose live operational state until a compliant Workflow query facade exists.
- A separate app introduces another deployment unit and OpenAPI surface.
- Limit/offset pagination is simpler but may later require cursor evolution for large mutable datasets.
- No auth means the app must remain local/non-public during this milestone.

## Rejected Alternatives

### Extend legacy `src/api/app.py`

Rejected because it couples Document Intelligence to competitor-price execution routes, CORS, telemetry, and existing boundary exemptions.

### Let API handlers import each runtime directly

Rejected because it violates R05 and spreads aggregation and privacy policy across transport handlers.

### Let Streamlit or FlowSync read runtime stores directly

Rejected because clients would become backend integration layers and could bypass contracts, authorization, lineage, and privacy controls.

### Add mutation endpoints now

Rejected because authentication, authorization, concurrency, idempotency, audit, and persistence contracts are not ready.

### Add database persistence in the API

Rejected because API Runtime must not become a second source of truth. Durable storage belongs behind runtime-owned services.

## Follow-Up

Implement the five phases in `docs/architecture/DOCUMENT_INTELLIGENCE_API_FOUNDATION_V1_IMPLEMENTATION_PLAN.md`. Do not add live providers or mutation routes until the required Workflow query facade and security decisions are separately approved.
