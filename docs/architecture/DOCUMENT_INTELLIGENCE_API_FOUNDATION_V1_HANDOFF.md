# Document Intelligence API Foundation v1 Handoff

**Milestone:** v0.9
**State:** Implemented and verified; closure commit and owner tag pending

## Current State

The repository contains an independent read-only Document Intelligence FastAPI application, deterministic local API data, hardened response boundaries, and an optional Streamlit API preview adapter. It is suitable for local contract and consumer integration work, but it is not authenticated, persistent, connected to live runtime state, or approved for public production exposure.

## Run The API

```text
python -m uvicorn src.api.document_intelligence.app:app --port 8001
```

Useful endpoints:

```text
GET http://127.0.0.1:8001/health
GET http://127.0.0.1:8001/api/v1/status
GET http://127.0.0.1:8001/api/v1/documents
```

## Run Streamlit

```text
streamlit run src/ui/streamlit/document_intelligence_app.py
```

Choose `api_preview` and use `http://127.0.0.1:8001`, or set `DOCUMENT_INTELLIGENCE_API_URL`. `local_preview` remains the default.

## Verification Commands

```text
python -m pytest tests/api/document_intelligence -q
python -m pytest tests/ui/streamlit -q
python -m pytest tests/review_runtime -q
python scripts/verify_boundaries.py
python -m py_compile src/api/document_intelligence/app.py
python -m py_compile src/ui/streamlit/document_intelligence_app.py
python -m pytest -q
git diff --check
```

## Important Files

- `src/api/document_intelligence/app.py`
- `src/api/document_intelligence/contracts.py`
- `src/api/document_intelligence/middleware.py`
- `src/api/document_intelligence/security.py`
- `src/api/document_intelligence/providers/local_provider.py`
- `src/api/document_intelligence/providers/facade_provider.py`
- `src/workflow_runtime/query_facade/`
- `src/api/document_intelligence/routers/`
- `src/ui/streamlit/api_client.py`
- `src/ui/streamlit/api_provider.py`
- `tests/api/document_intelligence/`
- `tests/ui/streamlit/`
- `docs/adr/ADR-014-document-intelligence-api-foundation.md`

## Extension Rules

- Keep API contracts consumer-neutral and version breaking changes under a new major path.
- Extend live reads only through approved public Workflow Query Facade source ports; the API adapter must not import individual runtime internals.
- Preserve strict envelopes, bounded pagination, request IDs, safe errors, security headers, and GET-only behavior until mutation architecture is approved.
- Keep Streamlit shaping in its provider/view-model layers and never make the UI a source of truth.
- Add privacy, OpenAPI, unavailable-state, method, boundary, and full-regression tests with every extension.
- Resolve identity, authorization, tenant isolation, persistence, idempotency, concurrency, and audit before adding any command endpoint.

## What Not To Change

- Do not connect routes directly to Review, Document, Entity, Transform, Matching, Workflow, storage, or telemetry internals.
- Do not expose raw documents, source rows, correction values, credentials, arbitrary metadata, exceptions, or stack traces.
- Do not enable permissive CORS or public deployment before authentication and gateway policy exist.
- Do not merge the new app into legacy `src/api/app.py` without a separate boundary decision.
- Do not modify root `dashboard.py` or competitor-price FlowSync as part of Document Intelligence work.

## Product Separation

Streamlit is the internal operator console and can use local or API preview data. Future FlowSync Document Intelligence remains a separately planned production client. Existing FlowSync Competitor Price remains a separate product with its own API and dashboard.

## Known Risks And Deviations

- API data is supplied by the preferred deterministic Workflow Query Facade adapter, with the API-local provider retained for compatibility; neither is live operational truth.
- No auth, tenant controls, persistence, production CORS, rate limiting, TLS policy, or telemetry exists.
- Optional Starlette TestClient transport requires undeclared `httpx2`; nine transport tests skip in the current environment, while direct and live smoke coverage passes.
- Boundary verification skips two pre-existing BOM-affected files.
- Limit/offset pagination may not suit future high-volume mutable datasets.

## Next Recommended Milestone

Complete Workflow Query Facade boundary/security verification, then plan trusted live source adapters together with identity, authorization, tenant, and persistence boundaries. Keep mutation endpoints deferred until those foundations and their audit/idempotency requirements are approved.
