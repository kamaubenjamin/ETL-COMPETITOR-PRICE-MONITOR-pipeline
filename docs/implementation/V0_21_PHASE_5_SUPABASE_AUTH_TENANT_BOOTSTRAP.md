# v0.21 Phase 5 Supabase Auth And Tenant Bootstrap

## Status And Scope

Phase 5 prepares hosted UAT authentication and tenant authority without deploying, creating a cloud user, or applying a migration. Supabase Auth authenticates an existing owner-created user; FastAPI verifies the access token and derives tenant, role, and permissions from RLS-protected membership data. Synthetic, non-confidential data remains mandatory and the target cost remains KSh 0.

This phase does not add document or Workflow Studio persistence, file storage, processing execution, OCR/LLM, ERP/export connectivity, workers, invitations, signup, OAuth, password recovery UI, MFA, or production execution.

## Implemented Architecture

```text
FlowSync browser
  -> Supabase Auth: email/password sign-in, session restore, refresh, sign-out
  -> Authorization: Bearer <Supabase access token>
FastAPI
  -> local asymmetric JWT verification through project JWKS
  -> Supabase Data API with the same user token + publishable key
  -> RLS returns only the user's active membership and active tenant
  -> fixed server role-to-permission mapping
  -> existing tenant-aware PermissionGuard and route checks
```

The API does not use a service-role key, shared JWT secret, full Supabase Python SDK, direct PostgreSQL connection, or persistent connection pool. JWKS and membership network calls are request-time only; `/health` and `/api/v1/health` make neither call.

## Trust Boundaries

- JWT signature, issuer, audience, expiry, optional not-before, subject UUID, algorithm, and signing key are verified before identity is accepted.
- JWT metadata, browser environment variables, and request headers cannot grant tenant, role, or permission authority.
- `user_metadata`, `app_metadata`, tenant headers, role headers, permission headers, actor headers, and local-demo headers are not authority inputs.
- The Data API request uses the verified user's bearer token. RLS limits membership reads to `auth.uid()`.
- Exactly one active membership and one active tenant are required. Zero or multiple rows fail with `403`.
- API `401` and `403` responses remain authoritative. The browser never retries a rejected mutation automatically.

## Frontend Authentication Flow

The app creates one lazy Supabase browser client from `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY`. The official client owns session persistence and refresh; FlowSync creates no custom token store.

1. The protected-route boundary restores the official Supabase session with an eight-second bounded loading state.
2. No protected route renders while restoration is unresolved.
3. An unauthenticated user sees email/password sign-in only. There is no signup, OAuth, anonymous, magic-link, or password-reset surface.
4. After Auth succeeds, FlowSync requests `GET /api/v1/session` to confirm authoritative tenant membership and receive only safe display context.
5. Server-returned workflow permissions may hide or disable controls but never grant API authority.
6. Sign-out clears the official active session and removes protected application access.

Sign-in failure always renders fixed non-enumerating copy. Raw Supabase errors, tokens, and configuration values are never rendered or logged.

## JWT Verification Flow

- Accepted algorithms: `RS256` and `ES256` only.
- `none`, `HS256`, missing or unsupported algorithms, missing or bad key IDs, malformed tokens, invalid signatures, expired tokens, future `nbf`, wrong issuer or audience, and missing or non-UUID subjects fail closed.
- Default issuer: `https://<project-ref>.supabase.co/auth/v1`.
- Default JWKS: issuer plus `/.well-known/jwks.json`.
- JWKS HTTPS URL and issuer must belong to `SUPABASE_URL`.
- Network timeout defaults to five seconds.
- Cache lifetime defaults to five minutes and cannot exceed ten minutes.
- At most eight verified public keys are retained by default.
- Verification errors expose only fixed `401` or `503` envelopes and never token contents.

The owner must confirm the Supabase project uses an asymmetric signing key; a legacy or shared-secret-only project does not satisfy this implementation. See [Supabase JWT verification](https://supabase.com/docs/guides/auth/jwts) and [signing keys](https://supabase.com/docs/guides/auth/signing-keys).

## Tenant Resolution And Database Access

The selected option is Supabase REST/Data API using the public publishable key and the verified user's bearer token. The query reads no browser-supplied tenant identifier. It asks for at most two active membership rows so ambiguity is detected. Inactive membership, inactive tenant, unknown role, no membership, malformed response, and multiple active memberships fail closed.

Rejected alternatives:

- Direct PostgreSQL: unnecessary connection, pooling, and serverless complexity.
- Service-role Data API: broader bypass authority than this one-user UAT requires.
- Supabase Python SDK: unnecessary for JWT/JWKS and one narrow REST lookup.

## Role-To-Permission Mapping

| Membership role | Effective Phase 5 permissions |
|---|---|
| `owner` | `document:read`, `document:list`, `workflow:read`, `workflow:create`, `workflow:edit`, `workflow:test`, `workflow:approve`, `workflow:publish`, `workflow:deactivate`, `workflow:admin` |
| `reviewer` | `document:read`, `document:list`, `workflow:read`, `workflow:test` |
| `viewer` | `document:read`, `document:list`, `workflow:read` |

Unknown roles fail closed. This mapping does not activate processing, export, file staging, or production workflow execution.

## Schema And RLS Summary

Migration `supabase/migrations/20260720140000_uat_identity_tenant_foundation.sql` creates only `public.app_tenants` and `public.app_tenant_memberships`. Both use UUID primary keys, constrained status and role values, timezone timestamps, and a unique tenant/user membership pair.

RLS is explicitly enabled on both tables. `anon` has no table privileges. `authenticated` receives only `select`; insert, update, and delete privileges are revoked and no write policy exists.

- Membership select policy: `auth.uid() = user_id` and active membership.
- Tenant select policy: active tenant connected to the user's own active membership.

No policy trusts JWT metadata. Bootstrap writes remain manual SQL-owner actions. See [Supabase RLS guidance](https://supabase.com/docs/guides/database/postgres/row-level-security).

## Manual Owner Bootstrap Checklist

### A. Configure Supabase Auth

1. Confirm an asymmetric RSA or EC signing key is active and the project JWKS endpoint returns public keys.
2. Enable email/password authentication and disable public self-service signup.
3. Decide whether the manually created UAT account requires email confirmation; record the owner decision outside Git.
4. Set Site URL to `https://<exact-flowsync-uat-host>`.
5. Add only the exact hosted URL, `http://127.0.0.1:4174`, and `http://localhost:4174` as redirect URLs.
6. Do not add production wildcards or unrelated preview URLs. See [Supabase redirect URL configuration](https://supabase.com/docs/guides/auth/redirect-urls).

### B. Apply And Inspect The Migration

1. Review and apply the migration through the Supabase SQL Editor or an owner-approved migration workflow.
2. Verify both tables, constraints, RLS enablement, policies, grants, and absence of anonymous access.
3. Do not add a seed UUID, email, password, key, document, or workflow row to the migration.

### C. Create The UAT Owner

1. Manually create one dedicated synthetic UAT user in Supabase Auth.
2. Use an owner-controlled test email and strong unique password.
3. Do not record the password or resulting Auth UUID in Git, tickets, screenshots, or deployment logs.

### D. Bootstrap One Tenant And Membership

Replace placeholders only in the private SQL Editor session:

```sql
begin;

with selected_tenant as (
    insert into public.app_tenants (slug, name, status)
    values ('<TENANT_SLUG>', '<TENANT_NAME>', 'active')
    on conflict (slug) do update
        set name = excluded.name, status = 'active', updated_at = now()
    returning id
)
insert into public.app_tenant_memberships (tenant_id, user_id, role, status)
select id, '<AUTH_USER_UUID>'::uuid, 'owner', 'active'
from selected_tenant
on conflict (tenant_id, user_id) do update
    set role = 'owner', status = 'active', updated_at = now();

commit;
```

Confirm the UAT user has exactly one active membership.

## Vercel Environment Checklist

Project A, FlowSync frontend — all values are public:

```text
VITE_DOCUMENT_INTELLIGENCE_API_BASE_URL=https://<exact-api-host>
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=<publishable-key>
VITE_DEPLOYMENT_ENVIRONMENT=uat
VITE_UAT_LABEL=UAT / Technical Preview
VITE_WORKFLOW_STUDIO_PERMISSIONS=
```

Project B, FastAPI:

```text
APP_ENV=uat
DOCUMENT_INTELLIGENCE_CORS_ALLOWED_ORIGINS=https://<exact-frontend-host>
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_PUBLISHABLE_KEY=<publishable-key>
SUPABASE_JWKS_URL=
SUPABASE_JWT_ISSUER=
SUPABASE_JWT_AUDIENCE=authenticated
SUPABASE_NETWORK_TIMEOUT_SECONDS=5
SUPABASE_JWKS_CACHE_SECONDS=300
SUPABASE_JWKS_MAX_KEYS=8
```

Blank JWKS and issuer overrides use deterministic values derived from `SUPABASE_URL`. Do not configure a service-role key, database URL, or shared JWT secret for this path.

## Smoke Test And Errors

After a separately authorized deployment and owner bootstrap:

1. Confirm `/health`, `/api/v1/health`, `/docs`, `/redoc`, and `/openapi.json` remain public.
2. Confirm an app route shows sign-in without flashing protected content.
3. Sign in and verify the UAT label, tenant name, owner role, and protected shell.
4. Confirm missing or invalid tokens return safe `401`; invalid membership or permissions return safe `403`; external JWKS or membership failure returns safe `503`.
5. Confirm local identity and tenant headers grant no hosted authority.
6. Confirm sign-out removes application access and refresh remains signed out.

All responses use fixed safe envelopes. Raw provider errors and token data remain internal.

## Rollback

1. Restore the previous frontend and API deployments through owner-controlled Vercel rollback.
2. Disable the UAT Auth user if access must be revoked immediately.
3. Rotate signing or publishable keys through Supabase owner controls if exposure is suspected.
4. Do not drop identity tables or policies automatically. Preserve them for review and use a separately approved rollback migration if removal is required.

## Verification Record

Completed locally on 2026-07-20 with synthetic configuration only:

- Clean temporary-copy `npm ci`: passed; 85 packages installed.
- Frontend validation, Auth validator, Vercel hosted-dist validator, typecheck, production build, lint command, and Workflow Studio validator: passed.
- Synthetic hosted bundle: no localhost URL, server secret name, raw JWT fixture, private key, or source map. The official Supabase client raises a non-blocking Vite chunk-size warning at approximately 507 kB minified.
- Document Intelligence API: 178 passed, including the final protected-route cases.
- Workflow Studio: 180 passed.
- Security: 69 passed.
- Full repository regression: 2,033 passed.
- Python dependency integrity and API compile check: passed.
- Runtime boundary verification: compliant, retaining two pre-existing BOM syntax warnings.
- Migration policy/static security tests and `git diff --check`: passed.
- The isolated local preview server started and stopped successfully. Visual browser automation was unavailable because the session exposed no browser backend.
- The high-signal repository scan found only the pre-existing literal placeholder `your-service-role-key` in the legacy root `Readme.md`; no secret value was found and Phase 5 does not consume that variable.

## Deferred Phase 6 Work

- Owner-operated deployment, cloud user creation, migration application, and hosted smoke testing.
- Exact redirect and CORS confirmation, free-tier monitoring, and pause recovery.
- Rate limiting, MFA, password recovery, invitations, production documentation-route review, and urgent cache-purge controls.
- Durable documents, Workflow Studio, storage, processing, OCR/LLM, ERP/export, workers, and production execution.
