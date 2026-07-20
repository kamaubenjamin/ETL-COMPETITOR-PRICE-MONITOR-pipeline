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

### Deliverables

- Pin Python 3.12 and add an explicit supported ASGI entrypoint.
- Replace the broad root install path for this function with a reviewed minimal API dependency manifest and bundle exclusions.
- Add strict configurable CORS for the exact FlowSync UAT origin.
- Define server-only environment loading/composition without enabling local demo headers as hosted authority.
- Preserve `/health`; decide whether `/docs`, `/redoc`, and `/openapi.json` remain exposed in UAT.
- Deploy Vercel Project B only after local import/startup/package checks pass.

### Stop Condition

No database migration, Supabase Auth integration, durable Workflow Studio store, runtime execution, bulk processing, ERP/export, OCR/LLM, or paid setting.

## Phase 4: FlowSync Deployment And API Wiring

### Deliverables

- Add Vercel SPA rewrite so direct refreshes of all React Router routes load `index.html`.
- Set `VITE_DOCUMENT_INTELLIGENCE_API_BASE_URL` to the Project B HTTPS origin.
- Add an explicit UAT/environment banner using a browser-safe variable.
- Keep permission hints non-authoritative and default to read-only until hosted identity exists.
- Deploy Vercel Project A and verify all direct routes, unavailable states, and API envelope handling.

### Stop Condition

No browser secret, service-role key, local identity masquerading as hosted authentication, or production integration.

## Phase 5: Hosted Auth, Tenant Bootstrap, And Environment Separation

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

Phase 1 runs only non-mutating checks:

```text
git status --short --branch

cd apps/flowsync-document-intelligence
npm run validate
npm run typecheck
npm run build

python -m compileall -q src/api/document_intelligence src/platform_runtime src/security src/workflow_studio
python -c "from src.api.document_intelligence.app import app; print(app.title)"
python -m pytest tests/api/document_intelligence/test_app.py tests/api/document_intelligence/test_health.py -q
python scripts/verify_boundaries.py

git diff --check
```

The build output is ignored and must not be added. Later phases add deployment-specific tests but must not broaden runtime behavior without explicit approval.
