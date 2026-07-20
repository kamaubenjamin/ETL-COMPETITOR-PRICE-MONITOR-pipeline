# Zero-Budget UAT Deployment v1 Implementation Plan

**Milestone:** v0.21

**Phase 1:** Complete - audit and documentation only

## Phase 1: Audit And Deployment Plan

### Delivered

- Audited deployment-facing repository layout, Python manifest/version state, FastAPI composition, CORS/auth/security, frontend build/API environment behavior, Supabase artifacts, GitHub workflow, ignore rules, and deployment documentation.
- Defined separate FlowSync and FastAPI Vercel projects with repository-root ownership and exact settings.
- Recorded current environment consumers and proposed variables without secret values.
- Classified deployment gaps from blocking today through production-only requirements.
- Recorded free-tier safeguards and the seven-phase delivery sequence.

### Stop Condition

No Vercel deployment, Supabase resource, migration, API/frontend behavior change, durable persistence, queue, production execution, integration, commit, push, or tag.

## Phase 2: Supabase UAT Project And Environment Preparation

**Status:** Complete; owner-operated cloud values remain private and application integration remains disabled.

### Implementation Record

- Added separate browser/server environment examples with no real values and explicit public/server-only classifications.
- Hardened ignore rules without excluding future Supabase migrations.
- Added a deterministic no-I/O `APP_ENV` and CORS-origin parsing contract; CORS remains disabled.
- Added a sanitized environment-driven FlowSync label with `Local Development` fallback and UAT technical-preview rendering.
- Documented manual dashboard, redirect, private bucket, zero-table/migration, deferred schema/RLS, and no-SDK decisions.
- Added targeted API configuration and frontend source checks. No Supabase runtime call, dependency, migration, deployment, or production behavior was added.

### Deliverables

- Owner-created Supabase Free project in a UAT-only organization/project boundary.
- Region, project URL, publishable key, server secret handling, Auth URL/redirect allowlist, and private Storage policy inventory.
- Explicit decision on whether Phase 3/4 deploy initially as read-only demo or wait for Phase 5 hosted identity.
- Confirmed database/table inventory. Current Document Intelligence API requires no Supabase table; do not create telemetry or Workflow Studio tables by assumption.
- Test-data retention/deletion rules, usage thresholds, pause/recovery notes, and owner-only dashboard access.

### Verification

- No secret in Git, Vercel frontend variables, browser bundle, screenshots, or documentation.
- Free plan and usage notifications confirmed.
- No public storage bucket or permissive database policy.

## Phase 3: FastAPI Serverless Compatibility And API Deployment

**Status:** Compatibility implementation complete; Vercel deployment intentionally not performed.

### Implementation Record

- Added `api/index.py` as a side-effect-free re-export of the existing FastAPI app.
- Pinned Python 3.12 and added an exact minimal API-only Vercel install manifest. Phase 6 initially proved an eager Workflow Runtime package import reached pandas, then a bundle-size hotfix moved the existing public Runtime facade to lazy exports. Clean startup now excludes pandas and NumPy, so the deployment manifest contains only FastAPI, the Supabase HTTP client, and JWT/crypto verification.
- Added minimal function bundle exclusions without excluding required `src` imports or adding frontend rewrites.
- Activated strict exact-origin CORS only when configured, with HTTPS required for hosted environments and no credentials.
- Rejected local-demo identity authority in UAT/pilot/production composition; hosted mutations remain fail-closed pending Phase 5.
- Verified health/docs routes, startup no-I/O, manifest policy, and process-local ephemeral state.

### Deliverables

- Pin Python 3.12 and add an explicit supported ASGI entrypoint.
- Replace the broad root install path for this function with a reviewed minimal API dependency manifest and bundle exclusions.
- Add strict configurable CORS for the exact FlowSync UAT origin.
- Define server-only environment loading/composition without enabling local demo headers as hosted authority.
- Preserve `/health`; decide whether `/docs`, `/redoc`, and `/openapi.json` remain exposed in UAT.
- Owner may deploy Vercel Project B only in a later authorized action after local import/startup/package checks pass and limitations are accepted.

### Stop Condition

No database migration, Supabase Auth integration, durable Workflow Studio store, runtime execution, bulk processing, ERP/export, OCR/LLM, or paid setting.

## Phase 4: FlowSync Deployment And API Wiring

**Status:** Deployment compatibility preparation complete; Project A and Project B deployment intentionally not performed.

### Implementation Record

- Added app-local Vercel Vite/install/build/output settings and an SPA rewrite excluding `/api`, assets, and file requests.
- Added a shared dependency-free API-origin resolver: local Vite development may use loopback HTTP, while hosted builds require a recognized environment and exact HTTPS API origin.
- Added an app-shell configuration guard with fixed safe copy so route content cannot issue requests under invalid hosted configuration.
- Retained the sanitized environment-driven UAT label on every route and prohibited a UAT production claim.
- Added Node 22 compatibility metadata, disabled production source maps, hardened the public environment template, and added source/deployment/hosted-dist validators.
- Documented Project A settings, Production/Preview branch behavior, exact API/CORS deployment order, fail-closed hosted mutations, and manual owner steps.

### Deliverables

- Add Vercel SPA rewrite so direct refreshes of all React Router routes load `index.html`.
- Set `VITE_DOCUMENT_INTELLIGENCE_API_BASE_URL` to the Project B HTTPS origin.
- Add an explicit UAT/environment banner using a browser-safe variable.
- Keep permission hints non-authoritative and default to read-only until hosted identity exists.
- Owner may deploy Vercel Project A only in a later authorized action, then verify all direct routes, unavailable states, and API envelope handling.

### Stop Condition

No browser secret, service-role key, local identity masquerading as hosted authentication, or production integration.

## Phase 5: Hosted Auth, Tenant Bootstrap, And Environment Separation

**Status:** Implementation preparation complete; no cloud user, remote migration, or deployment performed.

### Implementation Record

- Added official Supabase browser Auth for existing users only, protected routing, bounded session restoration, safe sign-in/out, and bearer propagation without custom token storage.
- Added asymmetric JWT verification with issuer/audience/time checks, bounded JWKS caching/timeouts, RLS-constrained Data API membership lookup, fixed role permissions, and a safe session endpoint.
- Added the minimal `app_tenants` and `app_tenant_memberships` migration with read-only authenticated RLS and owner-only bootstrap writes.
- Added deterministic JWT, membership, and migration tests plus the Phase 5 owner runbook. Hosted smoke testing remains Phase 6.

### Deliverables

- Add Supabase browser Auth using only URL and publishable key.
- Add API-side JWT verification through a real external `IdentityProvider`; do not trust identity or tenant headers from the browser.
- Map authenticated subjects to tenant membership and fixed platform permissions.
- Bootstrap synthetic UAT users/tenant through reviewed owner operations.
- Separate local, preview, and UAT configuration and redirect origins.
- Replace build-time Workflow Studio permission hints with API capability discovery when approved.

### Stop Condition

No service-role key in the frontend, wildcard tenant access, production user, customer document, or production environment reuse.

## Phase 6: Hosted Verification And Handoff

### Deliverables

- Health, docs-policy, auth, tenant concealment, role, CORS preflight, SPA deep-link, preview, lifecycle, privacy, and safe-error smoke tests.
- Verify cold-start/unavailable handling and in-memory Workflow Studio loss across redeploy/recycle.
- Verify private storage and RLS if those services become active.
- Check Vercel/Supabase usage dashboards and document recovery from free-tier pause.
- Produce UAT runbook, access list, test-data policy, limitations, and teardown instructions.

## Phase 7: Closure And Tag

### Deliverables

- Final architecture/implementation summary, handoff, release notes, verification evidence, roadmap/debt/changelog alignment, and tag recommendation.
- Confirm KSh 0 configuration, no secrets, no customer data, no production activation, and a clean branch.

## Verification Matrix

Phase 2 runs the approved local checks without cloud or Supabase network operations:

```text
git status --short --branch

cd apps/flowsync-document-intelligence
npm run validate
npm run typecheck
npm run build

python -m compileall -q src/api/document_intelligence src/platform_runtime src/security src/workflow_studio
python -c "from src.api.document_intelligence.app import app; print(app.title)"
python -m pytest tests/api/document_intelligence/test_app.py tests/api/document_intelligence/test_health.py -q
python -m pytest tests/api/document_intelligence -q
python -m pytest tests/workflow_studio -q
python scripts/verify_boundaries.py

git diff --check
```

The build output is ignored and must not be added. Later phases add deployment-specific tests but must not broaden runtime behavior without explicit approval.
