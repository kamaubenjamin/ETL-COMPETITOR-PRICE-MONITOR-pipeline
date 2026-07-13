# Document Intelligence API Foundation v1 Implementation Plan

**Milestone:** v0.9
**Status:** Phases 1-4 complete; Phase 5 pending

## 1. Milestone Overview

v0.9 delivers a separate read-only Document Intelligence API foundation for Streamlit and future FlowSync Document Intelligence consumers. Each phase is scoped for one Codex session and stops after focused implementation and verification. The legacy competitor-price API and dashboard remain unchanged.

## 2. Phase 1: API Contracts And App Skeleton

**Completion note:** Implemented the separate FastAPI factory, strict standard-library response contracts, safe errors, pagination metadata, and `/health`, `/api/v1/health`, and `/api/v1/status` routes. Domain data endpoints remain unimplemented. The active FastAPI/Starlette environment lacks its undeclared optional `httpx2` TestClient dependency, so transport-only TestClient assertions skip; route functions, OpenAPI, and live Uvicorn HTTP smoke checks provide endpoint verification without adding dependencies.

### Objectives

- Create the separate FastAPI application and `/api/v1/document-intelligence` router.
- Define strict health, collection envelope, safe error, document, processing, validation, matching, review, correction, reprocess, workflow, and audit response contracts.
- Define provider protocols and deterministic app dependency injection.
- Expose health and OpenAPI only; do not implement domain collection routes yet.

### Expected Files

Create:

- `src/api/document_intelligence/__init__.py`
- `src/api/document_intelligence/app.py`
- `src/api/document_intelligence/contracts.py`
- `src/api/document_intelligence/errors.py`
- `src/api/document_intelligence/providers.py`
- `src/api/document_intelligence/routes/__init__.py`
- `src/api/document_intelligence/routes/health.py`
- `tests/api/document_intelligence/__init__.py`
- `tests/api/document_intelligence/test_contracts.py`
- `tests/api/document_intelligence/test_app.py`

Do not modify `src/api/app.py`, `src/contracts/api.py`, `dashboard.py`, or competitor-price modules.

### Tests

- Contract JSON round trips, strict key/type validation, bounds, and version rejection.
- App creation without external services or database.
- Health response and safe unavailable-provider response.
- OpenAPI title, version, path prefix, and absence of mutation paths.
- Static import isolation and no competitor-price imports.

### Verification

```text
python -m pytest tests/api/document_intelligence/test_contracts.py tests/api/document_intelligence/test_app.py -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after contracts, app skeleton, health, and verification. Do not add domain endpoints.

## 3. Phase 2: Read-Only Document, Review, And Audit Endpoints

**Completion note:** Implemented the eleven requested `/api/v1` domain GET routes using an API-owned deterministic provider, defensive copies, stable ordering, bounded pagination, explicit safe filter validation, and privacy-safe document/review/correction/reprocess/workflow/audit projections. No live runtime, persistence, external service, or mutation dependency was added.

### Objectives

- Add deterministic provider records and all planned GET endpoints.
- Implement strict filters, stable sorting, bounded limit/offset pagination, empty results, not-found behavior, and safe errors.
- Exclude controlled correction values and raw artifact payloads.
- Keep providers defensive and dependency-free from backend runtime internals.

### Expected Files

Create or modify:

- `src/api/document_intelligence/providers/local_provider.py`
- `src/api/document_intelligence/routers/documents.py`
- `src/api/document_intelligence/routers/validation.py`
- `src/api/document_intelligence/routers/matching.py`
- `src/api/document_intelligence/routers/reviews.py`
- `src/api/document_intelligence/routers/workflows.py`
- `src/api/document_intelligence/routers/audit.py`
- `src/api/document_intelligence/app.py`
- `tests/api/document_intelligence/test_local_provider.py`
- `tests/api/document_intelligence/test_read_only_endpoints.py`

### Tests

- Every endpoint area, filter, pagination boundary, stable order, defensive copy, and empty response.
- Invalid enums/limits/offsets, unknown IDs, provider failures, and structured safe errors.
- Correction history excludes `new_value`, raw old values, and comments.
- Audit/validation/matching projections exclude raw rows, documents, candidates, credentials, and arbitrary metadata.
- `POST`, `PUT`, `PATCH`, and `DELETE` are not registered.

### Verification

```text
python -m pytest tests/api/document_intelligence -q
python -m pytest tests/ui/streamlit tests/review_runtime -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after deterministic read-only endpoints and verification. Do not connect Streamlit or live runtimes.

## 4. Phase 3: Streamlit API-Provider Adapter Preview

**Completion note:** Added explicit `local_preview` and `api_preview` modes, a GET-only standard-library API client with strict v1 envelope validation, and an API provider that preserves the console provider interface and view-model shapes. Local mode remains the default; API errors produce visible bounded empty states with no silent local fallback.

### Objectives

- Add an API-backed provider matching the Streamlit console's read-only semantic interface.
- Preserve `LocalOperatorConsoleProvider` as explicit deterministic mode.
- Add provider-mode labeling, contract-version validation, bounded timeouts, and clear unavailable/error states.
- Use deterministic in-process or mocked transport in tests; no external service dependency.

### Expected Files

Create or modify:

- `src/ui/streamlit/api_client.py`
- `src/ui/streamlit/api_provider.py`
- `src/ui/streamlit/data_providers.py`
- `src/ui/streamlit/document_intelligence_app.py`
- `src/ui/streamlit/components.py`
- `tests/ui/streamlit/test_api_client.py`
- `tests/ui/streamlit/test_api_provider.py`
- `tests/ui/streamlit/test_document_intelligence_app.py`

No FlowSync UI code is created in this phase.

### Tests

- API/local provider output parity for supported views.
- Contract-version mismatch, timeout, unavailable, malformed response, pagination, and empty results.
- No mutation methods, background writes, silent live-to-local fallback, or competitor imports.
- Existing v0.8 visual/read-only and Review Runtime preview regressions.

### Verification

```text
python -m pytest tests/ui/streamlit tests/api/document_intelligence -q
python -m pytest tests/review_runtime -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after the Streamlit adapter preview and verification. Do not implement authentication, live runtime providers, or FlowSync UI.

## 5. Phase 4: API Boundary And Security Hardening

**Completion note:** Added API-local request context and security policy modules, bounded client request-ID sanitization with safe generated IDs, consistent response/header propagation, generic unhandled-exception envelopes, explicit safe `404`/`405` handling, GET-only contract tests, security headers, and disabled-by-default CORS. No endpoint, dependency, runtime import, auth, persistence, or mutation capability was added. TestClient transport tests remain conditional because the active Starlette build requires optional undeclared `httpx2`; direct middleware tests and live Uvicorn checks cover the hardening behavior.

### Objectives

- Verify R05 with no new exemptions and codify forbidden imports.
- Harden method allowlist, query bounds, response sizes, safe errors, CORS defaults, request IDs, and exception handling.
- Add OpenAPI contract snapshot/compatibility coverage and privacy scans.
- Document deployment assumptions without implementing authentication or public deployment.

### Expected Files

Create or modify:

- `src/api/document_intelligence/app.py`
- `src/api/document_intelligence/errors.py`
- `src/api/document_intelligence/contracts.py`
- `tests/api/document_intelligence/test_security_boundaries.py`
- `tests/api/document_intelligence/test_openapi.py`
- `tests/boundaries/` only if a focused rule test is required
- `scripts/verify_boundaries.py` only if the new package is not already covered; explain any change

### Tests

- Unsupported mutation methods, oversized limits, malformed identifiers, unknown parameters, and safe 4xx/5xx envelopes.
- No wildcard CORS, secrets, file paths, stack traces, raw values, or high-cardinality logging.
- OpenAPI includes only approved v1 routes and stable response contracts.
- API has no direct imports from Document, Entity, Transform, Matching, Review, storage, telemetry, UI, or competitor modules.

### Verification

```text
python -m pytest tests/api/document_intelligence tests/boundaries -q
python -m pytest tests/ui/streamlit tests/review_runtime -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after API hardening and boundary verification. Do not add auth, database, mutation routes, or deployment infrastructure.

## 6. Phase 5: Verification, Documentation, And Release Closure

### Objectives

- Run focused API/UI/runtime, boundary, and full repository regression suites.
- Add architecture summary, handoff, and release notes.
- Update plan, ADR, roadmap, technical debt, and changelog accurately.
- Prepare but do not create the final tag.

### Expected Files

Create:

- `docs/architecture/DOCUMENT_INTELLIGENCE_API_FOUNDATION_V1_SUMMARY.md`
- `docs/architecture/DOCUMENT_INTELLIGENCE_API_FOUNDATION_V1_HANDOFF.md`
- `docs/releases/v0.9-document-intelligence-api-foundation.md`

Modify:

- `docs/architecture/DOCUMENT_INTELLIGENCE_API_FOUNDATION_V1_PLAN.md`
- `docs/architecture/DOCUMENT_INTELLIGENCE_API_FOUNDATION_V1_IMPLEMENTATION_PLAN.md`
- `docs/adr/ADR-014-document-intelligence-api-foundation.md`
- `docs/ROADMAP.md`
- `TECHNICAL_DEBT.md`
- `CHANGELOG.md`

### Verification

```text
python -m pytest tests/api/document_intelligence -q
python -m pytest tests/ui/streamlit tests/review_runtime tests/boundaries -q
python scripts/verify_boundaries.py
python -m pytest -q
git diff --check
git status --short --branch
```

Full-suite failures and generated-file changes must be reported exactly. Release notes must not claim authentication, authorization, persistence, live runtime integration, public deployment, or mutation readiness.

### Stop Condition

Stop after release closure. Do not commit, push, or tag unless separately instructed.

## 7. Cross-Phase Boundary Requirements

- New API code imports only Workflow Runtime public interfaces and approved shared utilities.
- Deterministic API providers do not import backend runtime internals.
- Streamlit communicates through provider interfaces and owns no API/runtime business logic.
- Future FlowSync Document Intelligence uses HTTP contracts only.
- Legacy `src/api/app.py`, competitor-price FlowSync, and `dashboard.py` remain untouched.
- Observability, if added later, is passive and fail-open.

## 8. Backward Compatibility

- No existing route is removed or changed.
- The Document Intelligence app uses a separate prefix and OpenAPI identity.
- API contract version 1 is additive within its major version; breaking changes require `/v2` and ADR review.
- Streamlit local deterministic mode remains available during v0.9.

## 9. Risks And Mitigations

| Risk | Mitigation |
|---|---|
| Legacy and new APIs become coupled | Separate package/app and no legacy modifications. |
| R05 blocks direct review/document reads | Deterministic provider first; future Workflow-owned query facade. |
| Scope expands into mutation/auth/persistence | Method allowlist, phase stop conditions, explicit non-goals. |
| API contracts become Streamlit-specific | Consumer-neutral models and client-side shaping. |
| Sensitive review/audit data leaks | Safe projections and dedicated privacy tests. |
| Full regression mutates generated files | Restore only documented generated artifacts before release commit. |

## 10. Definition Of Done

- Phases 1-5 are complete and individually verified.
- All planned read-only endpoint areas and deterministic providers are implemented.
- Streamlit API-provider preview passes parity and unavailable-state tests.
- No mutation route, live database, auth implementation, external service, OCR, LLM, or competitor dependency exists.
- R05 and boundary verification pass without new exemptions.
- Full regression passes and release documentation is complete.

## 11. Commit And Tag Strategy

Recommended one commit per phase:

1. `feat: add document intelligence api contracts`
2. `feat: add document intelligence read endpoints`
3. `feat: add streamlit api provider preview`
4. `test: harden document intelligence api boundaries`
5. `chore: close v0.9 document intelligence api foundation`

Recommended final tag after Phase 5 verification:

`v0.9-document-intelligence-api-foundation`
