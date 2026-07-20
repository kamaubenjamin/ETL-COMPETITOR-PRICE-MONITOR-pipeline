# Zero-Budget Vercel + Supabase UAT Deployment v1 Plan

**Milestone:** v0.21

**Phase 1 status:** Audit and plan complete; no cloud resources or deployments created

**Cost ceiling:** KSh 0; free tiers only

## Phase 2 Implementation Record

Phase 2 adds server and browser-safe environment templates, hardened ignore rules, a pure API environment/CORS parsing contract, a bounded visible UAT label, manual Supabase project/Auth/Storage/database setup guidance, and explicit secret classification. It does not create or call Supabase, enable CORS/Auth/storage/persistence, add an SDK/dependency/migration, deploy Vercel, or activate production behavior.

The owner-created Supabase project remains an unconnected UAT foundation. Current application table count is zero, Workflow Studio remains process-local, and the proposed future workflow/tenant table names are non-executable planning vocabulary only.

## Phase 3 Implementation Record

Phase 3 adds `api/index.py`, a Python 3.12 declaration, an exact API-only FastAPI dependency/install boundary, Vercel bundle exclusions, environment-aware exact-origin CORS, hosted local-demo identity rejection, and serverless import/health/statelessness verification. Workflow Studio remains process-local and ephemeral. API docs remain enabled for technical UAT. No Vercel deployment, Supabase integration, migration, production execution, or FlowSync behavior change occurs.

## Phase 4 Implementation Record

Phase 4 adds app-local Vite/Vercel settings and safe SPA routing, strict hosted API URL enforcement with a visible fixed configuration error, retained sanitized UAT labeling, Node/build/output declarations, disabled source maps, dependency-free deployment/dist checks, and manual Project A/API-CORS coordination. No Vercel deployment, hosted Auth, Supabase runtime, persistence, staging, or production behavior is activated.

## Phase 5 Implementation Record

Phase 5 adds existing-user Supabase browser Auth, protected routes and bearer propagation, asymmetric FastAPI JWT verification, RLS-constrained one-membership tenant resolution, fixed server-side UAT permissions, a safe session projection, and the minimal tenant/membership migration. No cloud user, remote migration, service-role key, deployment, document/workflow persistence, storage, processing, or production execution is activated.

## 1. Objective

Provide a controlled path to a hosted, non-production UAT environment using two Vercel projects, one Supabase Free project, and GitHub deployment integration. The environment is for test data and bounded product review only. It is not a production, pilot, bulk-processing, or execution-activation environment.

## 2. Target Architecture

```text
Browser
  -> Vercel Project A: FlowSync React/Vite static frontend
  -> HTTPS
  -> Vercel Project B: Document Intelligence FastAPI function
  -> Supabase Free: PostgreSQL, Auth, private limited UAT storage
```

Frontend and API remain separate Vercel projects. The API is serverless and stateless. Supabase is the future hosted identity/data/storage authority, but the current API has no Supabase Auth, PostgreSQL repository, or Storage adapter. Those integrations must be implemented in later reviewed phases.

## 3. Current Repository Findings

- FlowSync root directory is `apps/flowsync-document-intelligence`; it is a Vite 8 SPA with lockfile-controlled dependencies and `dist` output.
- Hosted frontend builds must set an exact HTTPS `VITE_DOCUMENT_INTELLIGENCE_API_BASE_URL`; invalid/missing configuration displays a fixed safe error and issues no route API calls. Only Vite development mode may use the loopback fallback.
- App-local `vercel.json` provides the SPA deep-link rewrite while excluding API, generated assets, and file-extension requests.
- Separate Vercel origins are prepared through an exact environment-driven CORS allowlist; the final Project A HTTPS origin remains a Phase 4 value.
- `api/index.py` is the supported wrapper and re-exports `src.api.document_intelligence.app:app` without duplicate construction.
- `requirements-api.txt` and the `vercel.json` install override prevent the broad root ETL/Streamlit/test manifest from being the intentional Project B dependency source.
- `.python-version` pins Python 3.12 without a competing runtime declaration.
- Default API composition has no startup I/O, background task, or lifespan hook. It uses in-memory demo/query providers and a process-local Workflow Studio provider. A shutdown hook exists only when an outer runtime composition is injected.
- `/health`, `/api/v1/health`, `/api/v1/status`, `/docs`, `/redoc`, and `/openapi.json` are available from the default FastAPI app.
- Default authentication is disabled. Reads use local in-memory data; management mutations fail closed. The browser client omits credentials and sends no bearer token.
- Optional SQLite Document State exists elsewhere in the platform, but is not composed by the default API. SQLite and tracked `Banks.db` must not be treated as serverless durable storage.
- No Supabase CLI config or migration directory exists. Existing Supabase code is a separate ETL telemetry REST client for `pipeline_runs`, `ingestion_logs`, and `operational_alerts`; the Document Intelligence API does not consume it.
- Phase 2 hardens `.gitignore` for real environment files, Vercel state, Supabase temporary/branch/cache state, and credential exports while preserving example templates and future migrations.

## 4. Recommended Vercel Projects

### Project A: FlowSync Frontend

| Setting | Recommendation |
|---|---|
| Root Directory | `apps/flowsync-document-intelligence` |
| Framework Preset | Vite |
| Install Command | `npm ci` |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Node.js | 22.x; Vite 8.1.4 requires `^20.19.0 || >=22.12.0` |
| Production/UAT branch | `platform/intelligent-document-processing` for this milestone; do not point `main` at UAT implicitly |
| URL role | Browser-visible UAT application origin |

Compatibility preparation is complete. Owner deployment remains gated on Hobby eligibility, exact API/frontend URLs, deliberate Production/Preview environment scopes, CORS coordination, and acceptance of incomplete Auth/read-only behavior.

### Project B: Document Intelligence API

| Setting | Recommendation |
|---|---|
| Root Directory | Repository root (`.`) so `src` imports remain available |
| Framework Preset | FastAPI (native Python auto-detection) |
| Install Command | `python -m pip install -r requirements-api.txt` (declared in `vercel.json`) |
| Build Command | None |
| Output Directory | None |
| Python | Pin and verify 3.12 |
| ASGI entrypoint | `api/index.py`, re-exporting `src.api.document_intelligence.app:app` |
| Production/UAT branch | `platform/intelligent-document-processing` for this milestone |
| URL role | HTTPS API origin used only by FlowSync UAT and approved diagnostics |

Compatibility prerequisites are implemented. Owner deployment remains gated on Hobby eligibility, exact settings/environment review, acceptance of incomplete Auth and ephemeral state, and the Phase 3 verification record. No `uvicorn` process command is required for a Vercel ASGI function.

## 5. Free-Tier Safeguards

- Use synthetic/test data only; never use real customer documents or confidential customer data.
- Never expose a Supabase service-role or secret key through `VITE_*`, source code, logs, or browser responses.
- Use only a publishable/anon key in the browser and only after RLS/auth policy review.
- Keep storage buckets private and use short-lived authorized access when storage is later enabled.
- Allow only the exact FlowSync UAT origin in CORS; do not use wildcard origins with authorization.
- Display an unmistakable UAT banner and environment label.
- Keep Workflow Runtime execution, ERP/export, OCR/LLM, staging, and production integrations disabled.
- Do not run background or bulk document processing in serverless requests.
- Bound request/sample sizes and UAT traffic. Rate limiting is deferred but required before pilot; until then access must remain tightly limited.
- Monitor Vercel and Supabase usage dashboards. Free-tier exhaustion should restrict or pause UAT, never trigger a paid upgrade automatically.
- Expect cold starts and Supabase inactivity pauses; provide no SLA.
- Confirm with the owner that this UAT qualifies for Vercel Hobby's personal, non-commercial fair-use terms. If it does not, the approved KSh 0 Vercel architecture is not viable and deployment must stop for a new hosting decision.

## 6. Platform Limits Used For Planning

As verified on 2026-07-20, Vercel Hobby is free for personal/non-commercial projects within included limits and can pause when limits are exceeded. Vercel documents Vite SPA rewrites, Python 3.12 as the default, and a 500 MB standard Python bundle limit. Supabase Free currently includes 500 MB database storage, 1 GB object storage, 5 GB egress, and 50,000 MAU, but free projects may pause after one week of inactivity and do not include production backups or uptime SLA.

Authoritative references:

- [Vercel Vite SPA guidance](https://vercel.com/docs/frameworks/frontend/vite)
- [Vercel Python runtime and entrypoints](https://vercel.com/docs/functions/runtimes/python)
- [Vercel Hobby plan](https://vercel.com/docs/plans/hobby)
- [Supabase Free plan](https://supabase.com/pricing)
- [Supabase billing and free-project behavior](https://supabase.com/docs/guides/platform/billing-faq)

Limits are operational assumptions, not repository guarantees. Recheck them immediately before each deployment phase.

## 7. Remaining v0.21 Phases

1. **Phase 1 - complete:** repository deployment audit, architecture, ADR, blocker classification, environment inventory, and implementation plan.
2. **Phase 2 - complete:** prepare the owner-created Supabase Free UAT foundation, Auth/Storage/database inventory, safe environment templates, secret/ignore policy, test-data rules, API configuration parsing, and visible UAT label without runtime integration or migrations.
3. **Phase 3 - compatibility complete, deployment deferred:** add FastAPI serverless compatibility, minimal dependencies, explicit Python/entrypoint configuration, strict CORS, and verified hosted safety without deploying Project B.
4. **Phase 4 - compatibility complete, deployment deferred:** add safe SPA routing/UAT labeling, enforce the hosted API URL, document exact Project A/CORS settings, and verify the static bundle without deploying.
5. **Phase 5 - implementation prepared, deployment deferred:** integrate hosted Supabase Auth, trusted asymmetric API JWT validation, RLS-constrained one-membership tenant bootstrap, fixed permission mapping, and UAT/environment separation without a service-role key.
6. **Phase 6:** run hosted smoke tests, CORS/security/privacy verification, free-tier monitoring checks, and UAT handoff.
7. **Phase 7:** close the milestone with final documentation, release notes, verification evidence, and owner tag recommendation.

## 8. Non-Goals

No production execution activation, durable Workflow Studio persistence, queue/worker, long-running processing, ERP/export, OCR/LLM, competitor-price behavior, Streamlit/dashboard modification, production SLA, or paid service is authorized by v0.21.
