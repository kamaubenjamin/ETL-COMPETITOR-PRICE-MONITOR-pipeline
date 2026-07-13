# Document Intelligence API Foundation v1 Summary

**Milestone:** v0.9
**Status:** Implemented and verified; closure commit and owner tag pending

## Milestone Purpose

v0.9 establishes a separate, versioned, read-only HTTP boundary for Document Intelligence consumers. It lets the internal Streamlit console preview API consumption without coupling the API to runtime internals, persistence, mutation behavior, or the separate Competitor Price product.

## Delivered Capabilities

- Separate FastAPI application under `src/api/document_intelligence/`.
- `GET /health`, `GET /api/v1/health`, and `GET /api/v1/status` foundation endpoints.
- Read-only document inbox/detail, processing, validation, matching, review case, correction history, reprocess plan, workflow run, and audit event endpoints under `/api/v1`.
- Strict JSON-compatible envelopes containing `success`, `data`, `error`, `metadata`, `api_version`, and `request_id`.
- Bounded limit/offset pagination metadata, deterministic ordering, defensive provider copies, and safe filters.
- API-owned deterministic local provider with no live runtime or external-service dependency.
- Streamlit `local_preview` and explicit GET-only `api_preview` modes; local preview remains the default.
- Bounded request-ID sanitization/generation and propagation through response bodies and headers.
- Privacy-safe `400`, `404`, `405`, and global `500` envelopes without raw exceptions or stack traces.
- `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`, and `X-Frame-Options: DENY`.
- Disabled-by-default CORS and GET-only OpenAPI/method verification.

## Phase Summary

1. **Contracts and skeleton:** Added the independent FastAPI factory, response contracts, safe errors, pagination, health, and status.
2. **Read-only endpoints:** Added eleven deterministic domain GET routes and privacy-safe API-owned projections.
3. **Streamlit adapter:** Added strict GET-only client/envelope validation and API-to-console provider mapping without silent local fallback.
4. **Boundary and security hardening:** Added request context, safe global errors, method restrictions, security headers, and explicit CORS policy.
5. **Release closure:** Ran focused and full verification and completed summary, handoff, release, roadmap, debt, and ADR updates.

## Final Module Structure

- `src/api/document_intelligence/app.py`: independent FastAPI factory and exception registration.
- `contracts.py`, `responses.py`, `errors.py`: strict envelopes, pagination, response builders, and safe errors.
- `middleware.py`, `security.py`: request IDs, fail-safe errors, headers, and CORS policy.
- `providers/local_provider.py`: deterministic defensive preview records.
- `routers/`: health, documents, validation, matching, reviews, workflows, and audit GET routes.
- `src/ui/streamlit/api_client.py`: bounded standard-library GET client.
- `src/ui/streamlit/api_provider.py`: console-provider adaptation.
- `tests/api/document_intelligence/` and `tests/ui/streamlit/`: contracts, endpoints, privacy, methods, security, and adapter coverage.

## Runtime Boundaries

The Document Intelligence API imports only its own package, the standard library, and existing FastAPI/Starlette dependencies. It does not directly import Review Runtime, Document Engine, Entity Runtime, Transform Runtime, Matching Runtime, Workflow Runtime, storage, telemetry, UI, Streamlit, FlowSync, or competitor-price internals.

The deterministic provider is preview-only. Future live data must be aggregated behind a public Workflow-owned query facade. Backend runtimes remain the source of truth, and the API remains a transport boundary.

## Consumer Model

- Streamlit supports `local_preview` and `api_preview`; local remains the default and API unavailability is visible without silent fallback.
- Future FlowSync Document Intelligence is a separate production UI and should consume versioned HTTP contracts only.
- Existing FlowSync Competitor Price, root `dashboard.py`, and legacy `src/api/app.py` remain separate and unchanged.

## Verification Results

- API tests: 22 passed, 9 skipped.
- Streamlit tests: 29 passed.
- Review Runtime tests: 175 passed.
- Full regression: 903 passed, 9 skipped, 711 warnings.
- Runtime boundary verification: compliant, with two pre-existing U+FEFF scan warnings.
- API and Streamlit entry points compile successfully.
- The nine skips are conditional Starlette TestClient transport tests because optional undeclared `httpx2` is unavailable; direct middleware tests and live Uvicorn smoke checks cover the same transport behavior.
- Full regression changed only four known generated artifacts; all were restored.

## Backward Compatibility

No legacy API route, competitor-price module, root dashboard, runtime contract, or mutation behavior changed. Streamlit local preview remains available and is still the default.

## Deferred Work

- Authentication, authorization, trusted identity, and tenant isolation.
- Rate limiting, production CORS, gateway, TLS, trusted hosts, and deployment policy.
- Database/persistence and a live Workflow-owned query facade.
- Mutation endpoints and their idempotency, concurrency, authorization, and audit contracts.
- TestClient/httpx dependency alignment and production telemetry.
- FlowSync Document Intelligence production UI.
- OCR, LLM processing, and external services.
