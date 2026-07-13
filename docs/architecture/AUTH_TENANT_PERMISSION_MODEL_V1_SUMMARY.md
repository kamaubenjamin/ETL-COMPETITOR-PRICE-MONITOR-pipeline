# Auth, Tenant, And Permission Model v1 Summary

**Milestone:** v0.15
**Status:** Implemented and verified; closed pending owner tag

## Milestone Purpose

v0.15 establishes a provider-neutral, default-deny security boundary for tenant-scoped Document Intelligence reads. It adds immutable identity and authorization contracts, deterministic local identities, tenant-aware document projections, guarded API reads, and a non-authoritative Streamlit auth preview while preserving the existing GET-only API and default local compatibility behavior.

The milestone does not add public mutations, production identity providers, token handling, writer enforcement, PostgreSQL/RLS, or tenant administration.

## Delivered Capabilities

- Provider-neutral contracts for principals, tenant scopes, authorization contexts, requests, decisions, and safe errors.
- Fixed role and permission catalogs with pure deterministic policy evaluation.
- Explicit anonymous, user, service-account, and system principal types.
- Deterministic local identity provider for local/demo/test composition only.
- Reusable `PermissionGuard` with tenant membership, explicit cross-tenant, and service-account checks.
- Tenant, workspace, ownership, creator, updater, source-system, and access-tag fields on `DocumentRecord`.
- Optional tenant narrowing across in-memory and SQLite document reads.
- Additive SQLite migration `002` with explicit tenant columns, indexes, and deterministic `tenant-local` legacy backfill.
- Tenant filters in Workflow Query Facade document and workflow read contracts.
- Opt-in API auth modes and centralized permission guards for every existing Document Intelligence GET route.
- Privacy-safe `401`, `403`, tenant-concealing `404`, provider-unavailable, and configuration failures.
- Streamlit `api_preview` controls for allowlisted local-demo identities without local permission decisions.
- Boundary, tenant-isolation, API compatibility, privacy, and full-regression verification.

## Phase Summary

1. **Security contracts and policy:** Added immutable principals, scopes, roles, permissions, contexts, decisions, safe errors, and default-deny policy.
2. **Identity and guards:** Added provider-neutral identity resolution, deterministic local identities, authorization requests, and `PermissionGuard`.
3. **Tenant-aware state and reads:** Added tenant-aware `DocumentRecord`, repository narrowing, migration `002`, Query Facade filters, and API-compatible projection.
4. **API guards:** Added explicit auth modes, API-local composition, centralized GET-route permissions, tenant narrowing, and safe denial behavior.
5. **Streamlit auth preview:** Added optional allowlisted local-demo identity headers and fixed safe unauthorized/unavailable display states while preserving default `local_preview`.
6. **Release closure:** Re-ran focused and full verification and completed summary, handoff, release, roadmap, debt, plan, ADR, and changelog documentation.

## Security Architecture

```text
Request / local demo identity
  -> IdentityProvider
  -> Principal
  -> AuthorizationContext
  -> AuthorizationRequest
  -> PermissionGuard
  -> Authorized tenant scope
  -> API provider / Query Facade tenant filter
  -> Document State repository narrowing
  -> Safe response / Streamlit preview
```

The API is the enforcement boundary. Query Facade and repositories apply guard-produced narrowing but do not decide roles. Streamlit may select a development identity but does not grant permissions or filter data as a security control.

## Authentication Modes

- `disabled`: default local compatibility; no identity is required and existing unauthenticated reads remain available.
- `local_demo`: explicit development-only identity resolution through the deterministic local provider.
- `authenticated`: provider-neutral placeholder requiring an injected non-local identity provider.
- `production`: fail-closed placeholder that rejects implicit local identities and requires approved production composition.

No mode parses tokens, creates sessions, or silently selects an external provider.

## Role Model

- `viewer`: document list/read and workflow read.
- `reviewer`: viewer permissions plus document review.
- `operations_manager`: reviewer permissions plus document approve and workflow run.
- `tenant_admin`: tenant-scoped operational, ingest, export, audit, tenant-admin, and user-admin permissions.
- `platform_admin`: fixed catalog access; cross-tenant use still requires explicit configuration and scope.
- `service_account`: no baseline wildcard; every tenant and permission is explicit.

## Permission Catalog

`document:read`, `document:list`, `document:ingest`, `document:review`, `document:approve`, `document:export`, `document:admin`, `workflow:read`, `workflow:run`, `audit:read`, `tenant:admin`, and `user:admin`.

## Tenant Rules

- Guard-produced tenant filters only narrow reads; client input cannot broaden scope.
- Missing, anonymous, or unknown identity denies when auth is enabled.
- Unauthorized detail reads are concealed as not found where identifier disclosure is a risk.
- Platform-admin cross-tenant access requires explicit application configuration.
- Service accounts require explicit tenant scope and permission grants.
- Public API projections do not expose internal tenant fields.

## API And Streamlit Compatibility

- Existing v0.9 paths, GET-only methods, payload meanings, envelopes, pagination, request IDs, and security headers are preserved.
- Default unauthenticated local API behavior is preserved under disabled mode.
- No POST, PUT, PATCH, DELETE, upload, or other public mutation route was added.
- Streamlit `local_preview` is unchanged and remains default.
- Streamlit `api_preview` may send only an explicitly selected allowlisted `X-Local-Identity`; it sends no token, credential, claim, or tenant override.
- API authorization remains authoritative.

## Privacy And Safety

Security, API, Query Facade, repository, and UI paths exclude tokens, credentials, raw claims, raw documents, raw rows, correction values, artifact payloads, storage paths, stack traces, and raw exception messages. Decisions and errors use bounded stable codes and fixed safe messages.

## Verification Results

- Security: 60 passed.
- Document Intelligence API: 59 passed, 9 skipped.
- Streamlit UI: 42 passed.
- Document State: 330 passed.
- Workflow Query Facade and Review Runtime: 239 passed.
- Full regression: 1,408 passed, 9 skipped, 711 warnings.
- Runtime boundary verification: compliant, with two pre-existing U+FEFF scan warnings.
- `git diff --check`: passed.

## Deferred Work

- Real identity providers and token verification.
- Supabase, Auth0, OAuth/OIDC, or other provider adapters.
- PostgreSQL, row-level security, and production tenant constraints.
- Public mutation/upload endpoints and writer authorization enforcement.
- Verified audit actor/tenant attribution persistence.
- Child-record tenant columns and cross-record tenant validation.
- Tenant/user administration, MFA, SSO, and session management.
- FlowSync authentication and ERP/export permission enforcement.
- Production composition and runtime selection.

