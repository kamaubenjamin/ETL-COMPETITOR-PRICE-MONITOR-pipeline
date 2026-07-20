# v0.21 Phase 2 Supabase UAT Foundation

## Status

Phase 2 is implemented as local configuration, safety boundaries, and an owner-operated Supabase dashboard checklist. No Supabase project was created by code, no network call was made, and no Auth, Storage, PostgreSQL repository, migration, Workflow Studio persistence, or Vercel deployment was activated.

Target owner resources:

- Organization: `FlowSync`
- Project: `flowsync-document-intelligence-uat`
- Plan: Free
- Environment: UAT / Technical Preview
- Data: synthetic and non-confidential only

## Supabase Foundation Summary

The repository now has separate safe environment templates for the server and browser. Ignore rules protect real environment files, Vercel local state, Supabase CLI temporary state, local branches/caches, and credential exports while preserving tracked `.env.example` templates and future `supabase/migrations/` files.

The server has a pure `APIEnvironmentConfig` parsing contract for `APP_ENV` and `DOCUMENT_INTELLIGENCE_CORS_ALLOWED_ORIGINS`. It performs no external call and does not enable CORS, authentication, persistence, or Supabase access. FlowSync can render a bounded environment label and safely defaults to `Local Development` when configuration is missing or invalid.

## Environment Templates

### Browser Template

`apps/flowsync-document-intelligence/.env.example` contains only browser-visible values:

| Variable | Phase 2 behavior |
|---|---|
| `VITE_DOCUMENT_INTELLIGENCE_API_BASE_URL` | Existing API client consumer; blank/missing safely uses the local URL |
| `VITE_SUPABASE_URL` | Reserved for Phase 5 Auth; no current consumer |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Reserved browser-safe key for Phase 5; no current consumer |
| `VITE_DEPLOYMENT_ENVIRONMENT` | Drives safe environment-label fallback, with `uat` mapped to the UAT label |
| `VITE_UAT_LABEL` | Optional bounded display label |
| `VITE_WORKFLOW_STUDIO_PERMISSIONS` | Existing public usability hint; blank grants nothing |

Every `VITE_*` value is public. The template contains no secret/service-role/database/JWT private value.

### Server Template

The root `.env.example` includes:

- Active Phase 2 parser inputs: `APP_ENV`, `DOCUMENT_INTELLIGENCE_CORS_ALLOWED_ORIGINS`.
- Reserved non-secret server names: `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`.
- Reserved server-only secrets: `SUPABASE_SECRET_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`, and future JWT settings.
- Existing optional ETL telemetry settings, disabled by default for Document Intelligence UAT.

`SUPABASE_SERVICE_ROLE_KEY` is retained because the existing optional ETL REST client recognizes that compatibility name. `SUPABASE_SECRET_KEY` is the future canonical secret-key name but has no Phase 2 consumer. Neither is required by the current API.

## Secret Classification

### Browser-Safe, Still Public

- Supabase Project URL.
- Supabase publishable/anon key after policy review.
- API public origin.
- Environment/UAT label.
- Workflow permission hints that grant no authority.

### Server-Only

- Supabase secret or legacy service-role key.
- Database password and direct/pooler database connection URLs.
- JWT shared secrets, private signing material, and private identity-provider configuration.
- Any future storage signing or administrative credential.

Server-only values must never appear in frontend files, `VITE_*`, Git, documentation examples, logs, screenshots, browser responses, or client-side error telemetry.

## Manual Owner Checklist

Perform these steps manually in the Supabase dashboard; do not paste collected values into Git or chat:

1. Sign in to Supabase and create or open the `FlowSync` organization.
2. Create or open `flowsync-document-intelligence-uat` on the Free plan.
3. Select the closest suitable available region to intended UAT users.
4. Generate a strong unique database password and store it in the owner's password manager.
5. Confirm the project is labeled and treated as UAT / Technical Preview.
6. Privately record the project reference and Project URL.
7. Privately record the publishable key for future browser Auth work.
8. Privately record the current secret/service-role key only for future server-side work.
9. Privately record direct and pooler connection strings and the database password; do not configure them in the application yet.
10. Do not create public buckets, paste server secrets into the Vercel frontend project, or reuse production credentials.
11. Record the local and future hosted Auth redirect URLs listed below.
12. Enable/confirm usage notifications and monitor database, Auth, Storage, and egress usage within Free limits.
13. Keep all data synthetic, bounded, non-confidential, and disposable.

No dashboard setting should claim that application integration is complete.

## Auth Preparation

Expected local site/redirect origins:

- `http://127.0.0.1:4174`
- `http://localhost:4174`

Future hosted placeholder:

- `https://<flowsync-uat-project>.vercel.app`

The exact Vercel Project A URL must replace the placeholder after Phase 4 deployment. The browser currently has no Supabase Auth client, session store, callback route, or token attachment. The API has no Supabase JWT/JWKS verification or hosted identity provider. Hosted mutations must remain disabled or explicitly demo-bounded until Phase 5 delivers real authentication, tenant membership, and permission composition. No fake success path is authorized.

## Storage Preparation

Future recommendation, not a created resource or integration:

- Bucket: `document-intelligence-uat`
- Access: private only; no public read policy
- Content: synthetic test fixtures only
- Credentials: publishable browser access only after policy review; never a service-role key in FlowSync
- Upload limits/file types: deferred to the real staging design
- Retention/deletion/signed URL policy: deferred and required before activation

Phase 2 adds no bucket, storage SDK, upload path, signed URL, file transfer, raw document handling, or staging behavior.

## Database And Migration Decision

Phase 2 requires no application tables and introduces no migration or `supabase/config.toml`. The current API does not depend on Supabase persistence. Workflow Studio remains process-local and disposable. Existing telemetry table expectations are legacy client configuration, not authoritative database migrations. RLS cannot be finalized until schemas, tenant ownership, operations, retention, and repository contracts are approved.

Possible future table names, all deferred and unimplemented:

- `tenants`
- `tenant_users`
- `workflow_definitions`
- `workflow_versions`
- `workflow_publications`
- `workflow_audit_events`

This list is planning vocabulary only. It is not a schema, migration authorization, column design, relationship design, or RLS policy.

## Configuration Boundary

`APIEnvironmentConfig`:

- normalizes local/test/UAT/pilot/production labels and reviewed aliases;
- parses at most 16 comma-separated HTTP(S) origins;
- rejects wildcards, credentials, paths, queries, fragments, invalid ports, and non-HTTP schemes;
- removes duplicate origins while preserving order;
- exposes only environment label and CORS configured/count metadata in its safe projection;
- ignores browser variables and reserved Supabase/database/JWT secrets;
- performs no file, network, database, Auth, or Supabase operation.

CORS middleware remains disabled until Phase 3 explicitly composes this contract into the API.

## Client Dependency Decision

No frontend Supabase SDK and no Python Supabase package is added. Environment preparation is sufficient for Phase 2. The existing legacy Python REST telemetry client remains isolated and is not imported into the Document Intelligence API. Actual browser Auth belongs to Phase 5.

## Verification

Completed locally on 2026-07-20:

- frontend source validation, typecheck, production build, lint command, and Workflow Studio validation passed;
- the Document Intelligence API suite passed with 126 tests and 9 intentional skips, and the Workflow Studio suite passed with 180 tests;
- targeted deployment/configuration and production-hardening tests passed with 11 tests;
- the Tier 1 runtime boundary verifier reported `COMPLIANT`; it retained two pre-existing BOM parse warnings outside this Phase 2 scope;
- 15 sensitive/local paths were confirmed ignored and three example/migration paths were confirmed visible to Git;
- sensitive template values were confirmed blank and a high-signal repository secret scan found no credentials;
- no `supabase/config.toml` or migration change exists, and `git diff --check` passed;
- label behavior is covered by source validation, typecheck, and the production build; a rendered browser inspection was attempted but the session exposed no browser backend.

The Vite build initially encountered a Windows sandbox denial while writing its local temporary cache. The same local-only build passed when rerun with workspace write approval. No external service, Supabase project, or deployment was contacted.
