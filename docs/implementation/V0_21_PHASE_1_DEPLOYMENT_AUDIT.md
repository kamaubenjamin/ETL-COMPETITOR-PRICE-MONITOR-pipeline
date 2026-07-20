# v0.21 Phase 1 Zero-Budget UAT Deployment Audit

## Audit Result

The repository is not deployable today as the approved two-project hosted UAT without small, explicit compatibility and security changes. The FlowSync production build itself is ready, and the FastAPI app imports/starts locally, but SPA routing, API entrypoint/dependency packaging, CORS, hosted identity, and environment hygiene remain open.

No deployment, cloud resource, migration, dependency, product behavior, or production activation was created in Phase 1.

## Frontend Vercel Audit

| Item | Verified result |
|---|---|
| Root Directory | `apps/flowsync-document-intelligence` |
| Framework | Vite React SPA |
| Install | `npm ci` from committed `package-lock.json` |
| Build | `npm run build` |
| Output | `dist` |
| Node requirement | Vite 8.1.4 declares `^20.19.0 || >=22.12.0`; recommend Vercel Node 22.x |
| API base URL | `VITE_DOCUMENT_INTELLIGENCE_API_BASE_URL`; defaults to `http://127.0.0.1:8001` |
| SPA rewrite | Missing; direct refresh of `/workflows`, `/uploads`, and other client routes is not ready |
| Browser credentials | Client uses `credentials: "omit"` and sends no bearer token |
| CORS dependency | Separate API origin requires `starlette.middleware.cors.CORSMiddleware`, already available through FastAPI; code/configuration changes are required but no new package is expected |
| Secrets | No frontend secret found; current source explicitly forbids credentials in Vite variables |
| Build output | `dist` is ignored |

All `VITE_*` values are embedded into the browser bundle. A Supabase publishable key can be browser-safe only with reviewed Auth/RLS/storage policies. A service-role or secret key is never browser-safe.

## FastAPI Vercel Audit

| Item | Verified result |
|---|---|
| ASGI import | `src.api.document_intelligence.app:app` |
| Vercel discovery | Not explicitly configured; nested `src/api/document_intelligence/app.py` is outside the documented direct `src/app.py` pattern |
| Required Phase 3 change | Add `tool.vercel.entrypoint` or a minimal supported entry file |
| Python declaration | None; CI uses 3.11, audit runtime is 3.12.13, Vercel currently defaults to 3.12 |
| Dependency manifest | Root `requirements.txt` only |
| Manifest risk | Includes Streamlit, pandas/numpy, Selenium, Playwright, ReportLab, pytest, and other non-API packages; Python bundles are not tree-shaken |
| Bundle scope | Repository root also contains tests, local data/runtime artifacts, backups, and non-API applications; Phase 3 needs reviewed `excludeFiles` rules without excluding imported `src` modules |
| Root Directory | Repository root (`.`) to preserve `src` package imports |
| Startup | Module creates one FastAPI app and process-local providers; no startup I/O or lifespan hook |
| Shutdown | Optional `composed.close` handler only when runtime composition is injected |
| Background work | No API `BackgroundTasks`, scheduler, worker, or queue found |
| Filesystem | Default app performs no required writes; optional SQLite/filesystem modules exist but are not default API persistence |
| SQLite | Platform supports optional SQLite; unsuitable as shared serverless UAT durability |
| Process-local state | Query/demo providers, export/upload placeholders, and Workflow Studio are memory-local and may reset or diverge across instances |
| Request-duration risk | Current reads are bounded/in-memory and preview is unavailable; broad imports/cold starts and any future processing are risks |
| Static data | Default API data is Python in-memory fixture data; tracked `Banks.db` is not an API dependency |
| Health | `/health` and `/api/v1/health` exist |
| Docs | Default FastAPI `/docs`, `/redoc`, and `/openapi.json` are available |
| CORS | `CORS_POLICY = "disabled"`; no `CORSMiddleware` |
| Auth | Default disabled; local demo provider is deterministic local-only; no external JWT/Supabase provider |

## Supabase Audit

- No `supabase/config.toml`, Supabase CLI directory, or Supabase migration set exists.
- No PostgreSQL schema or repository adapter exists for Document Intelligence or Workflow Studio.
- Workflow Studio uses a process-local in-memory store and does not persist to Supabase.
- Supabase Auth has no frontend client, session handling, API JWT verifier, identity provider, tenant bootstrap, or redirect configuration.
- Supabase Storage has no bucket contract, upload adapter, signed URL policy, retention policy, or API integration.
- Existing `src/integrations/supabase_client.py` is a server-side PostgREST client for legacy ETL telemetry. It expects optional `pipeline_runs`, `ingestion_logs`, and `operational_alerts` tables but the repository contains no migrations proving those tables.
- The currently composed Document Intelligence API requires **zero Supabase tables**. Phase 2 must inventory intended schemas without inventing migrations.
- Safe UAT policy is synthetic metadata/documents only, private buckets if enabled, strict RLS, least-privilege publishable browser access, server secrets only in Project B, bounded retention, and owner-controlled teardown.

## Environment Variable Inventory

### Browser-Safe / Project A

| Variable | Current consumer | Required now | Exposure | Destination | Code change |
|---|---|---:|---|---|---|
| `VITE_DOCUMENT_INTELLIGENCE_API_BASE_URL` | `src/api/client.ts` | Required for hosted frontend | Public origin | Project A | No |
| `VITE_API_BASE_URL` | None | No | Public origin | Do not configure | Yes, only if intentionally renamed/aliased |
| `VITE_WORKFLOW_STUDIO_PERMISSIONS` | `src/state/workflowPermissions.ts` | Optional | Public hint, never authority | Project A | No |
| `VITE_SUPABASE_URL` | None | No until Phase 5 | Public project URL | Project A in Phase 5 | Yes |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | None | No until Phase 5 | Public key, safe only with RLS | Project A in Phase 5 | Yes |
| `VITE_UAT_LABEL` | None | Required safeguard before UAT | Public display text | Project A | Yes |

### Server-Only / Project B

| Variable | Current consumer | Required now | Exposure | Destination | Code change |
|---|---|---:|---|---|---|
| `SUPABASE_URL` / `FLOWSYNC_SUPABASE_URL` | ETL `SupabaseClient`, not API startup | No | Server configuration | Project B only if an approved adapter uses it | Yes for API integration |
| `SUPABASE_SERVICE_ROLE_KEY` / `FLOWSYNC_SUPABASE_SERVICE_ROLE_KEY` | ETL `SupabaseClient`, not API startup | No | Secret | Project B only; never Project A | Yes for any API use |
| `DATABASE_URL` | None | No | Secret | Project B only if PostgreSQL adapter is approved | Yes |
| Auth/JWT issuer, audience, JWKS settings | None | Required before hosted auth | Server security configuration | Project B | Yes |
| CORS allowed origins | None | Required before separate-origin frontend | Server configuration | Project B | Yes |
| Environment/runtime mode | None; runtime config is caller-supplied | Required for explicit hosted composition | Server configuration | Project B | Yes |

### Local-Only / Existing Telemetry

`FLOWSYNC_TELEMETRY_ENABLED`, `FLOWSYNC_TELEMETRY_RAISE_ON_ERROR`, `SUPABASE_SCHEMA`, retry/timeout values, and telemetry table-name overrides are consumed by the optional ETL telemetry layer. They are not required by the Document Intelligence UAT API and should remain unset there unless separately reviewed.

## Deployment Blocker Classification

| Finding | Classification | Required action |
|---|---|---|
| Vercel Hobby is documented for personal, non-commercial use | Blocking policy decision today | Owner must confirm eligibility; otherwise stop and choose a different KSh 0 host/plan |
| CORS disabled for separate origins | Blocking today | Add strict configurable allowlist in Phase 3 |
| No supported explicit ASGI entrypoint | Blocking today | Add explicit Vercel entrypoint in Phase 3 |
| Broad root Python dependency bundle | Blocking today | Create reviewed minimal API manifest/bundle exclusions |
| Missing SPA rewrite | Blocking today | Add frontend-root `vercel.json` in Phase 4 |
| Hosted build falls back to localhost without API variable | Blocking today | Set actual current variable in Project A |
| Root ignores `.env` only, not `.env.*`/`.vercel` | Required before hosted UAT | Harden ignore rules before using cloud tooling |
| Default auth disabled; browser sends no token | Required before authenticated hosted UAT | Supabase Auth/JWT/identity integration in Phase 5 |
| Local demo identity headers | Required before hosted UAT | Do not expose as hosted authentication |
| No UAT banner | Required before hosted UAT | Add explicit environment label in Phase 4 |
| In-memory Workflow Studio | Acceptable UAT limitation if disclosed | Expect loss/recycle; no valuable authoring data |
| In-memory query/demo providers | Acceptable early UAT limitation | Synthetic demo review only |
| Free-tier cold starts/Supabase pauses | Acceptable UAT limitation | Safe unavailable UI and recovery runbook |
| API docs publicly available | Acceptable UAT limitation pending owner decision | Gate/disable before pilot if required |
| No rate limiter | Acceptable tightly restricted UAT limitation | Add/bound before pilot |
| SQLite and filesystem durability unavailable | Required before pilot | Use reviewed PostgreSQL/Supabase repositories |
| No durable audit/Workflow Studio store | Required before pilot | Add migrations, RLS, transactions, and repositories |
| No private storage adapter/retention policy | Required before pilot if documents are tested | Implement reviewed private storage boundary |
| No backup/SLA/compliance controls | Required before production | Paid/production architecture and operations review |
| No workers/long-running processing | Required before production processing | Separate queue/worker architecture; not Vercel requests |
| Runtime execution/ERP/export/OCR/LLM disabled | Required before production only if separately approved | Separate milestones and threat/operations review |

## GitHub And Secret Handling

- The only GitHub workflow validates contracts on pull requests and selected branches; it does not deploy Vercel or Supabase.
- Vercel Git integration should be used separately for Project A and B; deployment credentials need not be committed.
- Root `.env.example` contains placeholders only. It documents a service-role name, which is server-only.
- Phase 1 secret-pattern scan must cover tracked files while excluding generated/dependency directories and report names/locations only, not values.
- Add `.env.*` with an exception for `.env.example`, plus `.vercel/`, before CLI/project linking.

## UAT Limitations

- Test data only; no confidential or customer documents.
- No production SLA, backup guarantee, custom domain, or paid support.
- Zero-budget Vercel deployment is conditional on owner-confirmed Hobby-plan eligibility under current non-commercial fair-use terms.
- Free services may cold start, restrict usage, or pause after inactivity.
- Workflow definitions and audit intents may disappear on API recycle/redeploy or differ between concurrent instances.
- No real preview adapter, bulk document processing, background worker, production execution, export/ERP, OCR, or LLM.
- Initial hosted deployments may remain read-only until Phase 5 completes real Auth and tenant composition.

## Phase 1 Recommendation

Proceed to Phase 2 only after owner review of this audit. Do not deploy the current branch unchanged. Supabase project creation, entrypoint/CORS changes, and frontend rewrites each require their separately authorized phase.

## Phase 1 Verification Evidence

- FlowSync `npm run validate`: passed across 74 source files.
- FlowSync `npm run typecheck`: passed.
- FlowSync `npm run build`: passed; Vite emitted the ignored `dist` bundle.
- Python syntax compilation: 83 deployment-boundary files compiled in memory without writing bytecode.
- ASGI import: `src.api.document_intelligence.app:app` imported as Document Intelligence API v1 under Python 3.12.13.
- Targeted app/health tests: 5 passed, 3 skipped. The skips are the existing optional transport tests because Starlette `TestClient` requests an uninstalled `httpx2` extra; direct route/startup/schema checks passed without installing anything.
- Runtime boundary verification: compliant, with the two known unrelated U+FEFF warnings.
- High-signal tracked secret-pattern scan: no findings.
- `git diff --check`: passed with repository line-ending conversion warnings only.
- Final worktree contains only the four Phase 1 documents and four milestone-index updates; no dependency, deployment, cloud, migration, or generated file is tracked.
