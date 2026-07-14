# ADR-021: Production Composition And Runtime Selection

## Status

Accepted and implemented for v0.16. Runtime/config contracts, the pure fail-closed validation matrix, internal Document State/lifecycle/writer/Query Facade composition, API-owned app/provider/auth activation, non-authoritative Streamlit runtime preview, and production/boundary/privacy hardening are verified. The milestone is closed pending owner tag; production adapters remain deliberately deferred.

## Context

The platform has persistence-neutral Document State repositories, deterministic in-memory and SQLite implementations, lifecycle advancement, internal writers, a Workflow Query Facade, a facade-backed read-only API, provider-neutral security, tenant-scoped API guards, and Streamlit local/API preview modes.

These components are individually explicit, but no approved application boundary selects and wires all of them. Current local module defaults cannot safely determine production persistence, identity, auth, tenant scope, lifecycle truth, or provider activation. Selection inside routes, views, repositories, Query Facade, or writers would create hidden fallback and circular ownership.

## Decision

Create one outer composition package, `src/platform_runtime/`, responsible for:

1. parsing an explicitly supplied configuration mapping
2. validating a fixed runtime/backend/auth/provider compatibility matrix
3. constructing Document State repositories
4. injecting lifecycle advancement into all writers
5. constructing the Document State Query Facade adapter
6. constructing the facade-backed API provider
7. selecting API auth config and an injected identity provider
8. creating the Document Intelligence API app
9. exposing a serialization-safe runtime descriptor for consumers

All validation occurs before resource construction where possible. Composition returns no partial runtime after failure.

## Package And Boundary Decision

`platform_runtime` is an outer adapter/composition layer. It may import approved public contracts from Document State, Query Facade, lifecycle, writers, API, and security. None of those packages may import `platform_runtime`.

The package must not contain domain logic, route logic, authorization policy, persistence implementation, UI behavior, or provider-specific claims. Future PostgreSQL, Supabase, and identity adapters remain external adapter targets mapped into existing ports.

## Runtime Mode Decision

Use fixed modes:

- `local`
- `test`
- `demo`
- `local_api_auth`
- `pilot`
- `production`

The mode must be explicit. It is never inferred from environment shape, hostname, debug state, branch, secrets, or UI selection.

Local and test may use in-memory or explicit SQLite with disabled or local-demo auth. Demo and local-api-auth require local-demo auth and API preview. Pilot requires explicit SQLite and an injected non-local authenticated provider. Production requires an implemented production PostgreSQL adapter and production identity provider.

## Production Fail-Closed Decision

Initial v0.16 production composition is deliberately unavailable because production persistence and identity adapters are deferred. Production rejects:

- in-memory or SQLite persistence
- disabled, local-demo, or authenticated-placeholder auth
- local identity provider
- missing persistent backend configuration
- missing identity provider or required secret reference
- deferred `future_postgres` before implementation
- local Streamlit preview
- writer composition without lifecycle advancement
- guarded API without tenant-aware reads

There is no fallback to local, demo, SQLite, in-memory, or unauthenticated behavior.

## Configuration Decision

Configuration is immutable and loaded by a pure function from an explicitly supplied allowlisted mapping. Package import performs no environment access, environment mutation, file loading, or network call.

Core config stores choices and secret references, not secret values. Safe serialization reports capability booleans such as whether a SQLite path is configured, not the path itself. Errors contain stable codes and fields, never raw values, DSNs, credentials, claims, paths, or exceptions.

## Document State And Service Decision

The composition root calls existing `compose_document_state` and receives separate read/write surfaces. It constructs one `LifecycleAdvancementService`, injects it into all four writers, and constructs `DocumentStateQueryFacadeAdapter` from the read surface.

Writers do not construct repositories. Lifecycle service does not select a backend. Query Facade does not select persistence. Document State does not import API or security.

## API Decision

The API app factory accepts a validated `RuntimeConfig` or existing `RuntimeComposition`, constructs `FacadeDocumentIntelligenceProvider` from the composed facade, and maps disabled/local-demo auth into existing API auth contracts. Routes resolve the app-scoped provider through a narrow dependency rather than use the module-level singleton. Authenticated and production placeholders reject before runtime resource construction. Existing routes, methods, payloads, envelopes, request IDs, and headers remain unchanged.

The current module-level deterministic API app/provider remains an explicitly local compatibility entrypoint only and cannot be used by pilot or production composition.

## Streamlit Decision

Streamlit remains non-authoritative. `local_preview` remains the compatibility default and `api_preview` retains API URL and local-demo identity-header controls. Runtime/backend/auth labels shown in Phase 4 are explicitly display-only and do not activate a platform mode. Streamlit cannot construct runtime services, select a backend, broaden tenant scope, decide permissions, reflect raw errors, or silently fall back to fixtures. Enforced demo/pilot/production mode selection remains owned by composed application configuration, not UI controls.

## Compatibility Decision

- Preserve deterministic local/test behavior.
- Keep existing constructors and direct tests valid during migration.
- Keep API and Streamlit public behavior unchanged in approved modes.
- Require explicit composition for new runtime entrypoints.
- Treat compatibility defaults as non-production and test that production cannot reach them.

## Consequences

### Positive

- One owner controls resource construction and shutdown.
- Invalid combinations reject before serving requests or writing state.
- Core contracts remain provider-neutral.
- Local development remains simple and deterministic.
- Production safety does not depend on documentation alone.

### Negative

- API provider singleton access must be migrated to app-scoped injection.
- Composition introduces a new outer package and a larger integration-test matrix.
- Production remains unavailable until separate provider/backend milestones complete.
- Pilot operation remains constrained while child records are not fully tenant-aware.

## Alternatives Rejected

- **Selection inside API routes:** duplicates configuration and permits bypass.
- **Selection inside Query Facade:** couples reads to persistence.
- **Selection inside Document State:** couples repositories to API/security/runtime mode.
- **Selection inside Streamlit:** makes UI authoritative and unsafe.
- **Environment reads at import:** creates hidden, order-dependent behavior.
- **Automatic production fallback:** can serve or write against unintended local state.
- **Provider-specific core config:** leaks Supabase/PostgreSQL concerns into stable contracts.
- **Making production available with SQLite/local identity:** overstates readiness and weakens tenant/security guarantees.

## Deferred Decisions

- PostgreSQL/Supabase repositories, migrations, RLS, and provisioning.
- Real identity-provider, token, and secret-manager adapters.
- Child-record tenant migration and multi-tenant pilot approval.
- Security-aware writer command gateway and public mutations.
- Production deployment manifests, process supervision, telemetry, readiness, backup, and recovery.
- Sessions, MFA, SSO, tenant/user administration, and FlowSync authentication.

## Acceptance

ADR-021 is accepted when the package location, explicit mode matrix, fail-closed production posture, one-way boundaries, API injection strategy, lifecycle/writer wiring, and configuration safety rules are approved. Planning adds no source code, tests, dependencies, migrations, endpoints, or UI changes.
