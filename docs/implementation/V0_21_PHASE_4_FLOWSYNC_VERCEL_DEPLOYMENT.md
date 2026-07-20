# v0.21 Phase 4 FlowSync Vercel Deployment Preparation

## Status And Boundary

Phase 4 prepares the FlowSync Document Intelligence Vite application for an owner-operated Vercel Hobby UAT deployment. It adds app-local static deployment configuration, exact hosted API-origin enforcement, a safe configuration-error state, deployment validation, and dashboard instructions. It does not deploy Vercel, add hosted Auth, add a Supabase SDK/runtime, persist data, enable workflow execution, stage files, connect ERP/export, or add OCR/LLM.

The target remains `UAT / Technical Preview` using synthetic, non-confidential data at KSh 0. No real production domain or customer data is authorized.

## SPA Routing

App-local `apps/flowsync-document-intelligence/vercel.json` configures Vite, `npm ci`, `npm run build`, `dist`, and one SPA rewrite to `/index.html`.

The grouped negative-lookahead rewrite includes application routes while excluding:

- `/api` and `/api/*` so this frontend project never pretends to own backend routes;
- `/assets` and `/assets/*` so Vite-generated assets resolve directly;
- requests whose final segment has a file extension, such as icons, manifests, and `robots.txt`.

Direct visits and refreshes are validated for `/`, `/documents`, `/uploads`, `/workflow-runs`, `/workflows`, `/workflows/new`, workflow detail, and workflow editor paths. The configuration is inside the frontend project root and does not change the repository-root FastAPI project.

## Hosted API Configuration

`VITE_DOCUMENT_INTELLIGENCE_API_BASE_URL` is a public browser value and must contain only the exact API origin.

- Vite development mode may use `http://127.0.0.1:8001` when the variable is blank.
- A production-mode build refuses API access unless it has a recognized deployment environment and a configured API URL.
- UAT, pilot, and production accept HTTPS only.
- Local HTTP is limited to `localhost`, `127.0.0.1`, and `::1` during development.
- Paths, queries, fragments, embedded credentials, malformed URLs, non-loopback HTTP, unknown environments, and values over 2,048 characters are rejected.
- A trailing `/` is normalized away.

The shared resolver never logs or renders the configured value. When configuration is missing or invalid, the app shell retains the header and renders a fixed safe message instead of mounting route content or issuing API calls:

```text
Document Intelligence API is not configured for this environment.
```

No hosted build silently falls back to localhost.

## Environment Template

The app template contains:

```text
VITE_DOCUMENT_INTELLIGENCE_API_BASE_URL=
VITE_SUPABASE_URL=
VITE_SUPABASE_PUBLISHABLE_KEY=
VITE_DEPLOYMENT_ENVIRONMENT=uat
VITE_UAT_LABEL=UAT / Technical Preview
VITE_WORKFLOW_STUDIO_PERMISSIONS=
```

Every `VITE_*` value is public and embedded in the browser bundle. Supabase URL/publishable key names are reserved for Phase 5 and should remain unset now. A Supabase secret/service-role key, database URL/password, JWT secret, private signing material, or other server credential must never use a `VITE_*` name or appear in the frontend project.

`VITE_WORKFLOW_STUDIO_PERMISSIONS` is a display/usability hint only. Leaving it blank keeps mutation controls unavailable. It cannot grant API authority.

## UAT Label

The header remains visible on every registered route. With:

```text
VITE_DEPLOYMENT_ENVIRONMENT=uat
VITE_UAT_LABEL=UAT / Technical Preview
```

it renders `UAT / Technical Preview` using the existing restrained environment badge. Labels are trimmed, character-allowlisted, and bounded to 48 characters. UAT rejects a configured production claim and falls back to the UAT label. Missing local configuration renders `Local Development`. The label controls no API, identity, tenant, role, permission, or workflow behavior.

## Vercel Project A Settings

| Setting | Required value |
|---|---|
| Project name | `flowsync-document-intelligence-uat` |
| Repository | `ETL-COMPETITOR-PRICE-MONITOR-pipeline` |
| Production branch | `platform/intelligent-document-processing` |
| Root Directory | `apps/flowsync-document-intelligence` |
| Framework | Vite |
| Install Command | `npm ci` |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Node dashboard setting | `22.x` |
| Package engine boundary | `>=22.12 <23` |

Production environment variables:

```text
VITE_DOCUMENT_INTELLIGENCE_API_BASE_URL=https://<api-project>.vercel.app
VITE_DEPLOYMENT_ENVIRONMENT=uat
VITE_UAT_LABEL=UAT / Technical Preview
```

Do not configure Supabase browser variables until Phase 5. Do not attach a real production domain.

## Branch And Preview Behavior

- Set the UAT project's Production Branch to `platform/intelligent-document-processing`.
- Other branches may create Vercel Preview deployments.
- Configure Production and Preview environment variables deliberately; do not assume one scope inherits a safe value from another.
- Preview deployments must use preview/synthetic services or remain visibly unconfigured. They must not point at real production services.
- If an API allowlist does not include a preview's exact origin, that preview correctly remains unable to make cross-origin API calls.

## API And CORS Coordination

Never use wildcard CORS. Use this sequence:

1. Prepare/deploy Project B first with `APP_ENV=uat` and an exact temporary or final planned UAT frontend origin. A planned stable Project A hostname may be used; never use a wildcard or reflected origin.
2. Verify Project B `/health` and `/docs`, then record its exact HTTPS URL.
3. Configure Project A with that exact URL in `VITE_DOCUMENT_INTELLIGENCE_API_BASE_URL` and deploy it to obtain the exact frontend HTTPS URL.
4. Set Project B `DOCUMENT_INTELLIGENCE_CORS_ALLOWED_ORIGINS=https://<exact-frontend-url>`.
5. Redeploy Project B so the exact CORS allowlist is active.
6. Redeploy Project A only if its API URL changed, then verify browser/API behavior.

An initial frontend deployment may show an API unavailable/CORS failure until step 5. That is safer than a wildcard or reflected origin.

## Hosted Mutation And Auth Safety

Phase 5 Auth is not present. Hosted UAT therefore remains read-only or fail-closed:

- API `401`/`403` responses remain authoritative and map to fixed safe copy.
- Permission hints never grant authority; blank hints keep mutation controls unavailable.
- The browser sends no bearer token, local-demo identity header, tenant override, actor override, or fake signed-in state.
- Authorization failures are not automatically retried.
- Workflow publication language remains governance-only and does not claim production execution.
- Upload validation remains metadata-only; selected file content is not staged or transmitted.

## Privacy And Build Controls

- Production source maps are explicitly disabled.
- API errors are mapped to fixed messages; raw response internals and stack traces are not rendered.
- Environment values are not logged.
- `node_modules` and `dist` remain ignored/untracked.
- The hosted-dist validator rejects localhost API URLs, server-only secret names, local authority headers, and `.map` files.
- Only synthetic, non-confidential UAT data is allowed.

## Manual Owner Deployment Steps

### Project B: API first

1. In Vercel, import `ETL-COMPETITOR-PRICE-MONITOR-pipeline` as a new project.
2. Select production branch `platform/intelligent-document-processing` and repository-root Root Directory.
3. Confirm native FastAPI detection, Python 3.12, no build/output directory, and the Phase 3 API-only install strategy.
4. Add `APP_ENV=uat` for the intended UAT deployment scope.
5. Set `DOCUMENT_INTELLIGENCE_CORS_ALLOWED_ORIGINS=https://<temporary-or-final-planned-frontend-host>` using one exact UAT origin. Do not use `*`.
6. Deploy only after a separate deployment authorization.
7. Verify `/health` and `/docs`; privately record the exact API URL.

### Project A: FlowSync frontend

1. Import the same repository as a separate Vercel project named `flowsync-document-intelligence-uat`.
2. Set Production Branch to `platform/intelligent-document-processing`.
3. Set Root Directory to `apps/flowsync-document-intelligence`.
4. Select Vite and Node `22.x`; confirm `npm ci`, `npm run build`, and `dist`.
5. Add the exact API URL as `VITE_DOCUMENT_INTELLIGENCE_API_BASE_URL`.
6. Add `VITE_DEPLOYMENT_ENVIRONMENT=uat` and `VITE_UAT_LABEL=UAT / Technical Preview`.
7. Leave Supabase and Workflow Studio permission variables blank for Phase 4.
8. Deploy only after a separate deployment authorization and privately record the exact frontend URL.
9. Update Project B CORS to the exact frontend URL and redeploy Project B.
10. Redeploy Project A only if the configured API URL changed.
11. Test each direct route/refresh, the UAT label, safe error states, `/health`, API CORS, and read-only/fail-closed mutation behavior.

## Verification

Verification completed on 2026-07-20:

- `npm ci` passed in a clean temporary copy; the workspace copy was blocked by a pre-existing Vite process holding a native dependency file open.
- `npm run validate`, `npm run typecheck`, `npm run build`, the dedicated Workflow Studio validator, and the Vercel hosted-dist validator passed.
- `npm run lint` completed successfully and reported the repository's existing limitation that frontend lint rules are not configured.
- The configured UAT bundle contains the UAT label and fixed configuration-error copy, and contains no localhost API origin, server-only secret name, local authority header, or source map.
- Document Intelligence API regression: 144 passed, 9 skipped.
- Workflow Studio regression: 180 passed.
- Runtime boundary verification: compliant, with its two pre-existing BOM syntax warnings.
- `git diff --check` passed; line-ending conversion warnings are informational.
- Browser automation was unavailable because the session exposed no browser backend. The isolated Vite preview server itself started successfully and was stopped after the check.

Phase 4 stops before any Vercel deployment, commit, push, or tag.
