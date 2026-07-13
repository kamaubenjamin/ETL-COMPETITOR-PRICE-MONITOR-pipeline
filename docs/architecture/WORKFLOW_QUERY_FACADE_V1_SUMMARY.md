# Workflow Query Facade v1 Summary

**Milestone:** v0.10
**Status:** Implemented and verified; closure commit and owner tag pending

## Milestone Purpose

v0.10 establishes a Workflow-owned, read-only query boundary between the Document Intelligence API and future approved runtime read sources. It prevents the API from reaching into runtime implementations while preserving the v0.9 HTTP contract.

## Delivered Capabilities

- Public package at `src/workflow_runtime/query_facade/`.
- Frozen, JSON-compatible read models for documents, processing, validation, matching, reviews, corrections, reprocess plans, workflow runs, and audit events.
- Bounded limit/offset pagination with deterministic ordering.
- Fixed safe filters for document, review, workflow, and audit queries.
- Stable `invalid_query`, `not_found`, `source_unavailable`, and `internal_error` facade errors.
- Read-only structural `Protocol` ports with no mutation methods.
- Deterministic `InMemoryWorkflowQueryFacade` with immutable fixtures and defensive projections.
- `FacadeDocumentIntelligenceProvider` mapping public facade records into existing v0.9 API provider shapes.
- Safe facade-to-API error mapping to bounded `400`, `404`, `503`, and `500` outcomes.
- Recursive import, privacy, provider-conformance, API-parity, method, request-ID, and security-header verification.

## Final Architecture

```text
Document Intelligence API
        |
        v
FacadeDocumentIntelligenceProvider
        |
        v
Workflow Query Facade Port
        |
        v
InMemoryWorkflowQueryFacade
        |
        v
Immutable read models
```

The in-memory provider is deterministic preview infrastructure, not live operational truth. Future sources must implement narrow injected ports behind an approved composition boundary.

## Phase Summary

1. **Contracts and read models:** Added immutable projections, filters, pagination, safe errors, and read-only ports.
2. **In-memory provider:** Added deterministic fixtures, stable ordering, filtering, pagination, safe lookups, and structural port conformance.
3. **API adapter:** Added explicit facade-to-v0.9 provider mappings and made the facade-backed provider the preferred deterministic API source while retaining the API-local provider.
4. **Boundary and security verification:** Added recursive dependency checks, payload/privacy parity, GET-only route verification, and safe facade-error mapping.
5. **Release closure:** Re-ran focused and full regression suites and completed summary, handoff, release, roadmap, debt, plan, and ADR updates.

## Runtime Boundaries

- `query_facade` may import only standard-library and its own package modules.
- It must not import API, UI, runtime implementations, storage, telemetry, database, external-service, FlowSync, or competitor-price modules.
- The API adapter may import only Document Intelligence API-safe provider/error modules, standard library modules, and public facade exports.
- Future live reads must arrive through injected source adapters and ports, never direct cross-runtime imports.
- API Runtime retains ownership of HTTP validation, envelopes, request IDs, status codes, security headers, and CORS.

## API Compatibility

- All v0.9 paths remain unchanged.
- All endpoint methods remain GET-only.
- Successful payload meanings, response envelopes, pagination metadata, request IDs, and security headers remain unchanged.
- Unknown IDs and invalid queries retain privacy-safe error behavior.
- Streamlit `api_preview` remains compatible.

## Verification Results

- Workflow Query Facade: 62 passed.
- Document Intelligence API: 41 passed, 9 skipped.
- Streamlit: 29 passed.
- Review Runtime: 175 passed.
- Full regression: 984 passed, 9 skipped, 711 warnings.
- Runtime boundary verification: compliant, with two pre-existing U+FEFF scan warnings.
- Facade adapter and in-memory provider compile successfully.
- Full regression generated four known legacy artifacts; all were restored.

## Privacy And Safety

Read models and API projections exclude raw documents, source rows, correction values, artifact payloads, stack traces, storage details, and arbitrary unsafe metadata. Errors use bounded codes and safe messages rather than source exception text.

## Backward Compatibility

The milestone is additive. It does not change v0.9 endpoint paths, payload meanings, root `dashboard.py`, legacy `src/api/app.py`, Streamlit's provider contract, backend runtime ownership, or competitor-price modules.

## Deferred Work

- Live source adapters and an explicit composition root.
- Database or materialized read projections.
- Authentication, authorization, and tenant isolation.
- Rate limiting, production CORS, gateway, TLS, and deployment policy.
- Mutation endpoints and their idempotency, concurrency, authorization, and audit contracts.
- TestClient/httpx dependency alignment and production telemetry.
- FlowSync Document Intelligence UI.
- OCR, LLM processing, and external services.
