# Auth, Tenant, And Permission Model v1 Handoff

**Milestone:** v0.15
**State:** Implemented and verified; closed pending owner tag

## Current State

The platform has a provider-neutral security core, deterministic local identity composition, tenant-aware document projections, tenant-scoped read paths, guarded Document Intelligence API GET routes, and a read-only Streamlit auth preview. v0.16 Phase 3 adds API-owned runtime composition: disabled and local-demo runtime auth map to existing API behavior, while authenticated and production placeholders fail closed. Phase 4 adds display-only Streamlit runtime/auth labels and fixed safe mismatch/error states without local permission or tenant decisions. Auth remains disabled by default for compatibility. Production identity and write enforcement are not active.

## Important Files

- `src/security/`: principals, scopes, roles, permissions, policies, decisions, contexts, requests, guards, and identity-provider contracts.
- `src/security/providers/local.py`: deterministic local/demo/test identity provider.
- `src/api/document_intelligence/config.py`: explicit API auth modes and bounded header configuration.
- `src/api/document_intelligence/auth.py`: API-local identity/context composition and read authorization.
- `src/api/document_intelligence/app.py`: app-scoped runtime provider/auth activation with compatibility defaults.
- `src/api/document_intelligence/routers/`: permission declarations for existing GET routes.
- `src/api/document_intelligence/providers/facade_provider.py`: guard-produced tenant narrowing and safe public projections.
- `src/document_state/records.py`: tenant-aware `DocumentRecord`.
- `src/document_state/persistence/sqlite/schema.sql`: migration `002` tenant columns and indexes.
- `src/workflow_runtime/query_facade/`: tenant-aware read contracts and deterministic providers.
- `src/ui/streamlit/api_client.py`: optional allowlisted local-demo identity header.
- `src/ui/streamlit/api_provider.py`: fixed privacy-safe API preview error states.
- `docs/adr/ADR-020-auth-tenant-permission-boundaries.md`: governing decision.

## How To Verify

```text
python -m pytest tests/security -q
python -m pytest tests/api/document_intelligence -q
python -m pytest tests/ui/streamlit -q
python -m pytest tests/document_state -q
python -m pytest tests/workflow_runtime/query_facade tests/review_runtime -q
python scripts/verify_boundaries.py
python -m pytest -q
git diff --check
```

The full suite may regenerate `price_history.csv`, `src/canonical_products.json`, `src/schedules.json`, and `src/storage/workflow_history.json`. Restore only those known files when they were clean before verification.

## Extension Rules

- Keep `src/security/` provider-neutral and standard-library-only.
- Map external identities into `Principal`; do not leak provider claims into policies or records.
- Keep permission decisions in `PermissionGuard`, not routes, UI, repositories, or Query Facade implementations.
- Pass only guard-produced tenant scope into read providers.
- Require explicit cross-tenant configuration and audit attribution for platform administration.
- Give service accounts explicit tenant and permission scope only.
- Add production composition through a single reviewed composition root with no silent local fallback.
- Preserve v0.9 API payloads unless a separately approved contract milestone changes them.

## What Not To Change

- Do not enable local identities implicitly in production.
- Do not trust client tenant filters as authorization proof.
- Do not make Streamlit authoritative or add local security filtering.
- Do not let API or Streamlit import Document State persistence directly.
- Do not add writer authorization inside deterministic writer services; use a future command gateway.
- Do not expose tenant internals, tokens, credentials, claims, raw payloads, paths, stack traces, or raw exceptions.
- Do not modify legacy `src/api/app.py`, root `dashboard.py`, or competitor-price modules.

## Auth And Tenant Behavior

- Disabled mode preserves current local compatibility.
- Local-demo mode requires explicit local provider injection.
- Authenticated and production modes require a non-local provider and fail closed otherwise.
- Anonymous and unknown identities deny in enabled modes.
- Tenant selection narrows verified membership and cannot broaden it.
- Cross-tenant resource details are concealed where appropriate.
- Streamlit sends no identity header by default and no tenant override at all.

## Known Risks And Deviations

- Only `DocumentRecord` and selected read contracts are tenant-aware; child tables remain deferred.
- Existing legacy rows use deterministic `tenant-local` backfill.
- Production identity/token verification and PostgreSQL/RLS do not exist.
- Writer authorization and persisted verified actor attribution do not exist.
- Authenticated and production modes are composition placeholders, not deployment readiness claims.
- Nine optional API transport tests remain skipped.
- Boundary verification reports two pre-existing U+FEFF scan warnings.

## Next Recommended Milestone

Plan v0.16 Production Composition / Runtime Selection. Define one explicit composition root for API auth mode, identity provider, Document State backend, Query Facade source, and lifecycle/writer services. It must fail closed, preserve local/dev composition, and avoid adding public mutations or a provider-specific core model until separately approved.
