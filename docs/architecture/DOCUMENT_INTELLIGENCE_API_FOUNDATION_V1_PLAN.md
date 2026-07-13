# Document Intelligence API Foundation v1 Plan

**Milestone:** v0.9
**Status:** Phase 1 implemented; Phases 2-5 pending

## 1. Problem Statement

The platform now has deterministic backend runtimes and an internal Streamlit operator console, but UI consumers have no neutral Document Intelligence API boundary. Streamlit currently reads local providers, and a future FlowSync Document Intelligence product must not import runtime internals or reuse the competitor-price execution API as its backend.

v0.9 establishes a versioned, read-only API foundation between UI consumers and backend-owned query services. It does not make the API a source of truth, expose mutation commands, or connect directly to runtime stores.

## 2. Current State

- ADR-007 defines API Runtime as a thin external gateway that delegates to Workflow Runtime.
- `src/api/app.py` is a legacy FlowSync ETL/Competitor Price execution API with four temporary R05 boundary exemptions. It is not the Document Intelligence API foundation.
- v0.8 provides deterministic provider and view-model contracts suitable for a consumer preview, not a live backend integration.
- Review Runtime has public JSON-compatible contracts, but R05 prohibits API Runtime from importing Review Runtime directly.

ADR-014 refines ADR-007 for a separate read-only Document Intelligence surface. Existing competitor-price routes and `dashboard.py` remain untouched.

## 3. Goals

1. Define explicit `/api/v1/document-intelligence` contracts and route ownership.
2. Serve deterministic read-only document, processing, validation, matching, review, workflow, and audit projections.
3. Support Streamlit and future FlowSync Document Intelligence through the same HTTP contract.
4. Keep runtime services and stores authoritative.
5. Preserve R05 by depending only on Workflow Runtime public facades and approved shared utilities.
6. Establish pagination, filtering, privacy, error, health, versioning, and OpenAPI rules.
7. Provide a deterministic adapter path for v0.8 Streamlit without removing its local fallback.

## 4. Non-Goals

- Mutation endpoints for ingestion, corrections, decisions, reprocessing, workflow execution, or upload.
- Database schemas, repositories, migrations, or persistent API state.
- Authentication or authorization implementation.
- Production internet exposure, API gateway, rate limiter, OAuth/OIDC, RBAC, or tenant isolation.
- UI implementation or a FlowSync Document Intelligence application.
- Changes to competitor-price FlowSync, `dashboard.py`, or legacy competitor routes.
- OCR, LLM processing, webhooks, external services, or event streaming.

## 5. Proposed Architecture

The foundation has four layers:

1. **API contracts:** immutable JSON-compatible response, filter, pagination, health, and error models owned by the Document Intelligence API package.
2. **Query-provider protocol:** read-only methods for each endpoint area with deterministic ordering and defensive copies.
3. **Route layer:** thin FastAPI handlers that validate query parameters, call the provider, and serialize bounded response envelopes.
4. **Consumer adapters:** Streamlit and future FlowSync clients translate API responses into their own view models without owning backend rules.

The Phase 1-2 implementation uses a deterministic local provider. A later live provider must be supplied by a public Workflow Runtime query facade. Route handlers must never import Document, Entity, Matching, Transform, Review, storage, telemetry, or competitor-price internals.

## 6. Package And App Boundary

Planned package:

```text
src/api/document_intelligence/
  __init__.py
  app.py
  contracts.py
  errors.py
  providers.py
  routes/
```

The application is independently runnable and titled **Document Intelligence API**. It does not modify or mount into legacy `src/api/app.py` during v0.9 unless a later implementation phase proves composition boundary compliance. This avoids route, CORS, dependency, and product-ownership coupling with the existing FlowSync ETL API.

## 7. API Contract Conventions

- Base path: `/api/v1/document-intelligence`.
- Foundation health aliases are `/health`, `/api/v1/health`, and `/api/v1/status`; domain collection routes introduced later remain under the Document Intelligence base path.
- JSON only; UTF-8; UTC ISO-8601 timestamps.
- Read methods only: `GET`, plus framework-required `HEAD`/`OPTIONS` behavior.
- Stable deterministic ordering with documented tie-breaker IDs.
- Bounded `limit` and non-negative `offset` in v1; default 50, maximum 200.
- Unknown query parameters and unsupported enum values fail with structured `400` responses.
- Missing resources return structured `404`; unavailable providers return privacy-safe `503`.
- Response envelope includes `contract_version`, `items`, `total`, `limit`, `offset`, and `snapshot_at` for collection endpoints.
- Error envelope includes `code`, `message`, `request_id`, and optional safe field/path details; never raw payloads or stack traces.
- Breaking changes require a new path major version and ADR review.

## 8. Planned Endpoint Areas

| Method and path | Purpose | Key filters |
|---|---|---|
| `GET /health` | Process health and provider readiness without secrets or dependency internals | none |
| `GET /documents` | Inbox preview | document type, lifecycle status, workflow, limit, offset |
| `GET /documents/{id}/processing` | Stage/status timeline preview | limit, offset |
| `GET /documents/{id}/validation-issues` | Bounded safe validation issues | severity, limit, offset |
| `GET /documents/{id}/matching-results` | Candidate summary without raw master records | match status, limit, offset |
| `GET /review-cases` | Review queue projection | status, priority, assignee, limit, offset |
| `GET /review-cases/{id}` | One safe case summary | none |
| `GET /review-cases/{id}/corrections` | Correction history metadata without controlled values | limit, offset |
| `GET /review-cases/{id}/reprocess-plans` | Dry-run/request plan summaries | limit, offset |
| `GET /workflow-runs` | Workflow activity | workflow, status, limit, offset |
| `GET /audit-events` | Bounded safe audit projection | runtime, event type, case/document reference, limit, offset |

No endpoint returns full documents, complete rows, correction values, credentials, arbitrary metadata, executable configuration, or internal exception text.

## 9. Read Models

API read models are consumer-neutral and must not mirror Streamlit widget structures. They include stable IDs, lifecycle codes, safe summaries, timestamps, counts, confidence values, lineage references, and bounded metadata. Streamlit view models remain presentation-specific and translate these contracts into tables and labels.

Correction responses include correction ID, case ID, field path, operation, reason code, actor ID, timestamp, and lineage only. `new_value`, old raw values, and reviewer comments are excluded from v0.9.

## 10. Runtime Boundaries

- **API Runtime owns:** HTTP routing, API contracts, serialization, query validation, versioning, safe errors, and transport-level limits.
- **Workflow Runtime owns:** future public query facade and aggregation of runtime-owned projections.
- **Document/Transform/Matching/Review runtimes own:** artifacts, validation, matches, cases, corrections, decisions, audit, and state.
- **Streamlit and FlowSync own:** client transport, presentation, and local UI state only.

R05 remains authoritative: `src/api/` imports only Workflow Runtime public interfaces and approved shared utilities. Deterministic providers may live inside the API package for v0.9 tests, but live providers must not bypass the Workflow facade.

## 11. Streamlit Consumer Model

Phase 3 adds an API-backed provider implementing the same read-only semantic methods as `LocalOperatorConsoleProvider`. Streamlit chooses the provider through explicit local configuration and keeps the deterministic provider as a fallback for development and tests.

The adapter must define connect/read timeouts, map API errors to unavailable/empty UI states, validate response contract versions, avoid background mutation, and never silently fall back from a configured live endpoint in a way that could misrepresent operational state.

## 12. Future FlowSync Document Intelligence Model

Future FlowSync Document Intelligence consumes the same versioned HTTP contracts as an independent client. It does not import Streamlit providers, Python runtime internals, or competitor-price contracts. Authentication, tenant context, mutation commands, and production CORS are separate future milestones.

Existing FlowSync Competitor Price keeps its current API and product lifecycle. No v0.9 route, contract, or package uses competitor-price terminology or imports.

## 13. Privacy And Security Architecture

- Read-only route allowlist; mutation methods are absent and tested as rejected.
- Strict bounded query parameters, collection sizes, strings, and metadata.
- No raw documents, source rows, controlled correction values, comments, secrets, tokens, or stack traces.
- Low-cardinality health/status output; no environment paths or dependency credentials.
- CORS denied by default in the new app; explicit origins are deferred until authenticated clients exist.
- API documentation exposure, trusted hosts, request-size limits, rate limits, TLS, authentication, and authorization are deployment/security follow-up work.
- Logs contain request IDs, route templates, status codes, and timings only; query values require allowlisting before logging.

## 14. Testing Strategy

- Contract round trips, strict fields, version rejection, JSON compatibility, and OpenAPI schema snapshots.
- Deterministic provider ordering, filtering, pagination, defensive copies, and empty results.
- Endpoint success, invalid query, not found, unavailable provider, unsupported method, and safe error tests.
- Privacy tests for corrections, audit, validation, matching, health, logs, and exception responses.
- Boundary tests proving no direct imports from backend runtime internals or competitor-price modules.
- Streamlit adapter parity tests against the local provider and unavailable/timeout response handling.
- Full existing UI, Review Runtime, boundary, and repository regression suites.

## 15. Operational Impact

v0.9 adds an optional API process only. Backend runtime execution must not depend on the API being available. The deterministic provider requires no network or external service. Live query latency, caching, service-level objectives, deployment topology, and scaling remain deferred.

## 16. Risks

| Risk | Mitigation |
|---|---|
| New API duplicates legacy `src/api/app.py` | Separate package, app, title, prefix, and ownership; no legacy route modification in v0.9. |
| Read endpoints bypass runtime ownership | Enforce R05 and require a Workflow-owned query facade for live data. |
| UI-shaped contracts constrain future clients | Keep API models consumer-neutral; shape inside each client. |
| Sensitive values leak through reviews or audit | Explicit safe projections, deny unknown metadata, and privacy serialization tests. |
| Read-only API is mistaken for production-ready security | Document no auth/public exposure; deny CORS by default and defer deployment. |
| Pagination changes produce unstable pages | Require stable sort keys and deterministic tie-breaker IDs. |
| Streamlit silently shows stale fallback data | Label provider mode and prohibit silent fallback when live mode is configured. |

## 17. Definition Of Done

- A separate versioned Document Intelligence FastAPI app and strict read-only contracts exist.
- All planned endpoint areas return deterministic bounded projections through provider protocols.
- No mutation route, database, external service, OCR, LLM, or competitor-price dependency is introduced.
- Streamlit can preview the API provider while preserving its local deterministic mode.
- R05 and all runtime boundaries are compliant without new exemptions.
- Privacy, method allowlist, pagination, errors, OpenAPI, UI parity, and full regressions pass.
- Summary, handoff, release notes, and recommended tag are complete.
