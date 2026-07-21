# ADR-026: Zero-Budget Vercel + Supabase UAT Boundary

## Status

Accepted and implemented for the v0.21 UAT / Technical Preview boundary. Phase 6 verified the deployed Vercel frontend and API, Supabase browser Auth, asymmetric JWT verification, RLS-constrained active tenant membership, fixed owner permissions, exact-origin CORS, and protected read-only document access. Phase 7 release closure is in progress. No production activation or further cloud action is authorized by this ADR alone.

## Context

The platform has a Vite/React FlowSync application and a FastAPI Document Intelligence API, but current composition is local/process-bound. The owner needs a hosted UAT environment at KSh 0 using existing Vercel and Supabase accounts. The environment must expose enough product surface for controlled review without being mistaken for production readiness.

Current gaps include no SPA deep-link rewrite, disabled API CORS, no supported Vercel ASGI entrypoint declaration, a broad Python dependency manifest, disabled/default local authentication, no hosted JWT identity provider, no PostgreSQL/Supabase repositories, and process-local Workflow Studio state.

## Decision

Use three independently governed deployment units:

```text
Browser
  -> Vercel Project A: FlowSync static Vite SPA
  -> HTTPS and strict CORS
  -> Vercel Project B: stateless FastAPI function
  -> Supabase Free: PostgreSQL, Auth, private UAT storage
```

Use separate Vercel projects rather than combining frontend and API. Project A owns static browser delivery and SPA routing. Project B owns server-only identity validation, tenant/permission enforcement, API composition, and future Supabase access. Supabase owns hosted Auth/data/storage only after each adapter/schema/policy is explicitly implemented.

## Authority And Data Decisions

- The browser may contain the API origin, Supabase URL, publishable key, and display-only UAT labels. Every `VITE_*` value is public.
- Supabase service-role/secret keys, database credentials, JWT verification configuration, and server policy remain in Project B only.
- The API must validate authenticated identity and derive tenant/permissions; the browser cannot assert identity, tenant, role, or management authority.
- Storage buckets remain private. Only synthetic data is allowed.
- Workflow Studio may remain in-memory for early UAT with explicit loss-on-recycle warnings. Durable Workflow Studio persistence is not authorized in Phase 1.
- Optional local SQLite and `Banks.db` are not serverless UAT persistence.
- Existing ETL Supabase telemetry tables are outside the Document Intelligence UAT data model and must not be repurposed silently.
- Phase 2 requires zero application tables. Future tenant/workflow names remain deferred planning vocabulary and do not authorize migrations or RLS.
- Phase 3 enables CORS only for explicitly configured exact origins; hosted origins require HTTPS, credentials remain disabled, and hosted Auth/JWT validation remains a Phase 5 authority boundary.
- Phase 4 rewrites only frontend SPA routes, requires an exact hosted HTTPS API origin, displays a safe configuration failure instead of using localhost in hosted builds, and keeps permission hints non-authoritative.
- Phase 5 uses the official Supabase browser client for existing-user email/password Auth, verifies asymmetric access tokens locally through JWKS, and resolves authority through RLS-constrained membership reads using the user token and publishable key. No service-role key, shared JWT secret, browser tenant selector, or direct PostgreSQL connection is required.

## Serverless Decision

Treat the FastAPI deployment as stateless and request-bounded. Do not run schedulers, background workers, browser automation, bulk document processing, or production runtime execution inside Vercel Functions. Cold starts, concurrent instances, and process recycling make in-memory state opportunistic only.

Use `api/index.py` to re-export the existing app, Python 3.12, an API-only FastAPI dependency manifest, and explicit bundle exclusions. Strictly allow the exact FlowSync UAT origin through CORS. Health remains lightweight; API docs remain enabled during bounded UAT technical testing and must be reconsidered before production.

## Cost Decision

Use Vercel Hobby and Supabase Free only. Vercel currently restricts Hobby to personal, non-commercial use, so owner confirmation of eligibility is a deployment gate; if business UAT is ineligible, this zero-budget target is blocked and must be redesigned. Do not enable paid add-ons, custom domains, paid backups, larger compute, or automatic upgrades. Monitor both dashboards and accept restriction/pause when free quotas are reached. Recheck plan limits and terms before deployment because they can change.

## Alternatives Rejected

- **One Vercel project for UI and API:** obscures deployment ownership, complicates roots/bundles, and weakens independent CORS/runtime configuration.
- **Deploy the current root dependency set unchanged:** risks oversized/slow Python functions because Vercel does not tree-shake Python dependencies.
- **Use local SQLite/Banks.db as hosted durability:** serverless files are not a durable shared database.
- **Expose local demo identity headers:** not authentication and unsafe for hosted authorization.
- **Put a service-role key in FlowSync:** all Vite variables are browser-visible.
- **Create inferred Supabase tables now:** schema, RLS, ownership, retention, and migration design are not approved.
- **Activate processing/runtime execution in UAT:** incompatible with the bounded serverless and zero-budget phase.

## Consequences

### Positive

- Clear frontend/API/security ownership and independent deployments.
- KSh 0 target with automatic HTTPS and Git-based previews.
- Supabase can later provide managed identity and durable data behind existing policy boundaries.
- Current safe API/UI states can be hosted before production execution exists.

### Negative

- Cross-origin configuration is mandatory.
- Workflow Studio state can disappear until separately persisted.
- Hosted authentication requires new API and frontend work.
- Free-tier cold starts, pauses, limited logs, storage, and lack of SLA constrain UAT.
- Root repository bundling and dependency scope require deliberate Phase 3 work.

## Acceptance

ADR-026 is satisfied for Phase 1 when the audit, environment inventory, project settings, blocker classifications, safeguards, and phased implementation plan are reviewed. Deployment requires separate phase authorization.
