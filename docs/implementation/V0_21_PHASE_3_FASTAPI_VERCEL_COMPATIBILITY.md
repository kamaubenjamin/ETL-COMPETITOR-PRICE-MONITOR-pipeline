# v0.21 Phase 3 FastAPI Vercel Compatibility

## Status And Boundary

Phase 3 makes the existing Document Intelligence FastAPI application compatible with a stateless Vercel UAT function. It does not deploy Vercel, create a cloud resource, add Supabase persistence/Auth/Storage, create a migration, enable production execution, or modify FlowSync behavior.

The deployment remains a technical preview for synthetic, non-confidential data. Authentication is incomplete. Workflow management mutations remain fail-closed, upload staging and export execution remain unavailable, and local identity headers are not accepted as hosted UAT authority.

## Entrypoint And Project Root

- Vercel Root Directory: repository root (`.`)
- ASGI entrypoint: `api/index.py`
- Exported object: `app`
- Source application: `src.api.document_intelligence.app:app`

The entrypoint only imports and re-exports the existing FastAPI instance. It constructs no alternate app, adds no routes, performs no file write or network call, and contains no deployment-specific business logic. Repository-root project ownership keeps the `src` package importable.

## Minimal Dependency Strategy

`requirements-api.txt` is the reviewed API-only install manifest. Phase 6 hosted deployment exposed an incomplete Phase 3 packaging assumption: importing the existing app also traverses `platform_runtime`, `workflow_runtime`, and the eager `src.transforms` package exports, which require pandas during module import. The manifest therefore directly pins `fastapi==0.139.2`, `httpx==0.28.1`, `PyJWT[crypto]==2.10.1`, and `pandas==3.0.2`. Their declared dependencies remain transitive. Vercel does not need `uvicorn` for an ASGI function.

The root `requirements.txt` remains the broad local ETL/Streamlit/test manifest and is intentionally not the Project B install source. `vercel.json` sets the exact install command:

```text
python -m pip install -r requirements-api.txt
```

This prevents Streamlit, Selenium, Playwright, ETL scraping/PDF packages, pytest, development tools, and unrelated competitor-price dependencies from being intentionally installed into the API function. NumPy, python-dateutil, and tzdata are installed transitively by pandas and are not duplicated as direct pins.

## Python Runtime

The root `.python-version` contains `3.12`, a mechanism supported by Vercel's Python runtime. It is the only Python version declaration in the repository. Local verification must run on Python 3.12 before deployment.

## CORS Policy

`APIEnvironmentConfig` remains the only environment parser. `create_document_intelligence_app` adds CORS middleware only when `DOCUMENT_INTELLIGENCE_CORS_ALLOWED_ORIGINS` contains one or more valid exact origins.

- Hosted UAT/pilot/production origins must use HTTPS.
- HTTP is accepted only for `localhost`, `127.0.0.1`, or `::1` in local/test environments.
- Wildcards, credentials, paths, queries, fragments, invalid ports, reflected origins, and non-HTTP(S) schemes are rejected.
- Allowed methods: `GET`, `POST`, `PATCH`.
- Allowed request headers: `Accept`, `Content-Type`, `X-Request-ID`.
- Exposed response header: `X-Request-ID`.
- Credentials are disabled.
- Missing configuration installs no CORS middleware, so browser cross-origin access stays disabled.

Phase 4 frontend origin placeholder:

```text
https://<future-frontend-project>.vercel.app
```

Replace it with the exact Project A HTTPS origin after that project exists. Do not add preview wildcards.

## Hosted Runtime And Authority Safety

`APP_ENV` recognizes local/development, test, UAT/technical-preview, pilot, and production. UAT, pilot, and production app composition rejects local-demo identity authority. Supplying `x-local-identity` or `x-tenant-id` does not enable hosted mutations. Supabase JWT verification remains Phase 5 work; no fake authentication success exists.

The default hosted composition retains:

- no platform runtime execution composition;
- disabled authentication and fail-closed management mutations;
- empty/read-only upload and export providers;
- no queue, worker, scheduler, background task, OCR/LLM, ERP, or export execution;
- no Supabase, database, or external network startup call.

## Serverless Filesystem And Import Audit

| Finding | Classification | Phase 3 result |
|---|---|---|
| Default API app, routers, middleware, responses, Auth contracts | Safe | Imports and constructs without required file writes, network calls, or current-working-directory data |
| Default facade/local query providers | Safe but process-local | In-memory fixture/query state only; not durable or shared |
| Workflow Studio provider | Safe but ephemeral | New process-local provider per app; definitions, validation/test evidence, publication state, and audit intents may disappear |
| Optional `platform_runtime` SQLite backend | Not composed in default API path | No SQLite path or shared file database is selected by the Vercel entrypoint |
| Injected runtime shutdown hook | Safely optional | Registered only when an outer runtime composition is explicitly supplied; the entrypoint supplies none |
| Root `data/`, generated outputs, Streamlit/dashboard, ETL and competitor-price modules | Not imported in API startup path | Excluded from the function bundle where supported |
| Packaged source under `src` | Required | Not broadly excluded because API routers/providers transitively require platform/security/workflow packages |

No deployment blocker was found in the default startup path. Vercel's packaged filesystem must still be treated as read-only; writable temporary space is not application durability.

## Statelessness And UAT Limitations

Each Vercel instance may have separate in-memory query and Workflow Studio providers. Instances can recycle at any time. Workflow definitions and publication records are process-local, ephemeral, may disappear after restart, and are not durable. State written during one request may not be visible to another request routed to a different instance. No persistence is added in Phase 3.

This makes hosted UAT suitable only for technical API/UX review, health checks, schema exploration, and bounded synthetic demonstrations. It is not suitable for durable workflow authoring, publication evidence, production operations, customer data, or execution activation.

## Health And API Documentation

The re-exported app preserves:

- `GET /health`
- `GET /api/v1/health`
- `GET /api/v1/status`
- `/docs`
- `/redoc`
- `/openapi.json`

Docs remain enabled for UAT technical testing. Production configurability is deferred. Health responses retain their existing safe envelope and do not expose environment values, secrets, filesystem paths, dependency versions, or internal exception details.

## Vercel Project B Settings

| Setting | Required value |
|---|---|
| Project name | `flowsync-document-intelligence-api-uat` |
| Git repository | `ETL-COMPETITOR-PRICE-MONITOR-pipeline` |
| Branch | `platform/intelligent-document-processing` |
| Root Directory | Repository root (`.`) |
| Framework | FastAPI (native Python auto-detection) |
| Python | `3.12` from `.python-version` |
| Build command | None |
| Output directory | None |
| Install command | `python -m pip install -r requirements-api.txt` from `vercel.json` |
| Entrypoint | `api/index.py`, exporting `app` |

Initial environment variables:

```text
APP_ENV=uat
DOCUMENT_INTELLIGENCE_CORS_ALLOWED_ORIGINS=https://<future-frontend-project>.vercel.app
```

`SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` may be recorded privately later if a reviewed server consumer needs them; the current API does not require either. Do not configure `SUPABASE_SECRET_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`, or JWT values for Phase 3 merely to make the project appear integrated.

## Packaging Controls

`vercel.json` excludes tests, frontend assets/builds, local data, docs, notebooks, scripts, virtual environments, generated reports/output, dashboard entrypoints, and development metadata from `api/index.py` where supported. It does not exclude `src`, because that package contains the required API and transitive runtime/security/workflow contracts. It contains no frontend SPA rewrite.

## Deployment Gate

Before the owner creates/deploys Project B:

1. Confirm Vercel Hobby eligibility for the intended zero-budget UAT usage.
2. Confirm the project settings above and no automatic paid upgrades.
3. Add only the exact UAT CORS origin available at deployment time; if Project A does not yet exist, leave CORS empty.
4. Keep all secret values in Vercel server environment settings, never Git or browser variables.
5. Run the Phase 3 verification matrix on Python 3.12.
6. Accept that Auth is incomplete, mutations are unavailable, and state is ephemeral.

Phase 3 stops before deployment.

## Verification

Completed locally on Python 3.12.13:

- `api/index.py` compiled and re-exported the same FastAPI instance as `src.api.document_intelligence.app:app`;
- OpenAPI inspection retained `/health`, `/api/v1/health`, the existing API routes, and UAT documentation routes;
- the API suite passed with 144 tests and 9 intentional skips;
- the Workflow Studio suite passed with 180 tests;
- the security suite passed with 60 tests;
- the focused deployment/CORS/entrypoint/serverless/health selection passed with 27 tests and 3 existing optional-transport skips;
- the Tier 1 runtime boundary verifier reported `COMPLIANT`, retaining two pre-existing BOM parse warnings outside Phase 3;
- `requirements-api.txt` validated offline against the installed exact FastAPI version and `vercel.json` parsed as valid JSON;
- frontend source validation retained the browser/server secret boundary;
- high-signal secret, prohibited-package, migration, forbidden-file, and diff checks passed.

The practical full repository regression completed with 1,989 passing tests and 9 skips. Its single failure was the pre-existing root `test_pipeline.py` integration path because archived/internal extraction data and browser connector output were unavailable. That ETL/competitor-price path is not imported or bundled by the API entrypoint and was not modified. Generated tracked artifacts from that optional run were restored to their pre-run content.
