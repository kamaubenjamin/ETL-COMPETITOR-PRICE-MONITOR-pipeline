# Production Composition / Runtime Selection v1 Handoff

**Milestone:** v0.16
**State:** Implemented and verified; closed pending owner tag

## Current State

The platform has an explicit, validated outer runtime composition for deterministic local/test/demo operation. It can compose in-memory or explicit file-backed SQLite Document State, lifecycle advancement, internal writers, Query Facade, an app-scoped API provider, and disabled/local-demo API authorization. Streamlit can display safe runtime labels but remains a read-only consumer.

Pilot is constrained and production is deliberately unavailable. No PostgreSQL/Supabase repository, real identity provider, token verifier, secret resolver, or production deployment composition exists.

## Important Files

- `src/platform_runtime/modes.py`: fixed runtime mode catalog.
- `src/platform_runtime/config.py`: immutable runtime configuration and safe projection.
- `src/platform_runtime/validation.py`: compatibility matrix and fail-closed validation.
- `src/platform_runtime/composition.py`: top-level internal composition and bundle invariants.
- `src/platform_runtime/document_state.py`: Document State, lifecycle, writer, and Query Facade assembly.
- `src/platform_runtime/security.py`: runtime-to-API auth mapping.
- `src/platform_runtime/api.py`: composed API provider/app helpers.
- `src/api/document_intelligence/app.py`: app-owned runtime activation.
- `src/ui/streamlit/runtime_preview.py`: display-only safe runtime labels.
- `docs/adr/ADR-021-production-composition-runtime-selection.md`: governing decision.

## How To Verify

```text
python -m pytest tests/platform_runtime -q
python -m pytest tests/api/document_intelligence -q
python -m pytest tests/ui/streamlit -q
python -m pytest tests/security -q
python -m pytest tests/document_state -q
python -m pytest tests/workflow_runtime/query_facade tests/review_runtime -q
python scripts/verify_boundaries.py
python -m pytest -q
git diff --check
```

The full suite may regenerate `price_history.csv`, `src/canonical_products.json`, `src/schedules.json`, and `src/storage/workflow_history.json`. Restore only those known generated files when they were clean before verification.

## Extension Rules

- Keep runtime selection explicit and validate before constructing resources.
- Add adapters at the outer boundary and map them into existing ports.
- Keep `platform_runtime` free of domain, route, policy, and UI logic.
- Preserve one-way imports: core packages must never import `platform_runtime`.
- Keep API providers app-scoped for composed applications.
- Require explicit backend paths/provider availability; never silently fall back.
- Keep runtime summaries and errors redacted and bounded.
- Preserve existing API contracts unless a separately approved milestone changes them.

## What Not To Change

- Do not enable production with SQLite, in-memory persistence, local identities, or placeholder auth.
- Do not let API routes, Streamlit, Query Facade, repositories, lifecycle services, or writers select runtime dependencies.
- Do not expose paths, provider references, tokens, credentials, environment values, claims, stack traces, or raw exceptions.
- Do not turn Streamlit labels into an authority or silently fall back from API preview to local fixtures.
- Do not modify legacy `src/api/app.py`, root `dashboard.py`, or competitor-price modules.

## Runtime And Resource Ownership

Entrypoints supply explicit `RuntimeConfig`. Validation precedes resource construction. `RuntimeComposition` owns the composed Document State resources, lifecycle service, writer bundle, and Query Facade and exposes an idempotent close hook. API construction consumes either config or a validated composition and stores app-scoped dependencies. Streamlit consumes API responses and safe display labels only.

## API And Streamlit Boundaries

The API remains the authoritative read and authorization boundary. Its default compatibility factory remains local-only; new composed entrypoints should use validated runtime composition. Streamlit retains `local_preview` and `api_preview`, performs no backend/auth/tenant decisions, and cannot activate pilot or production.

## Known Risks And Deviations

- Production and fully authenticated pilot modes cannot start without future adapters.
- SQLite is local/dev durability, not the production target.
- Child records are not fully tenant-keyed and writer authorization remains deferred.
- Shutdown ownership is minimal for current local resources.
- Nine optional API transport tests remain skipped.
- Boundary verification reports two pre-existing U+FEFF scan warnings.

## Next Recommended Milestone

Plan v0.17 Product UI / FlowSync Document Intelligence integration. Keep FlowSync as a separate API consumer, define its operator and authentication boundary first, and do not couple it to Streamlit, repositories, `platform_runtime`, or competitor-price internals.

