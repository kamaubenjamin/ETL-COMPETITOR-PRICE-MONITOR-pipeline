# Production Composition / Runtime Selection v1 Plan

**Milestone:** v0.16
**Status:** Phases 1-4 implemented; Phases 5-6 not started

## 1. Problem Statement

The platform has explicit components for durable state, Query Facade reads, lifecycle advancement, internal writers, API authorization, and Streamlit preview, but no single approved composition root wires them together. Current module-level defaults are useful for deterministic tests and local preview, yet they cannot safely decide production persistence, identity, tenant enforcement, or writer/lifecycle activation.

v0.16 defines one outer runtime composition boundary that validates an explicit operating mode, selects only compatible adapters, constructs services in dependency order, and fails closed for unsupported or incomplete production combinations.

## 2. Goals

1. Define immutable runtime mode and configuration contracts.
2. Make backend, auth, identity-provider, API-provider, writer, lifecycle, Query Facade, and Streamlit selection explicit.
3. Preserve deterministic local, demo, and test workflows.
4. Reject unsafe production defaults and incomplete production dependencies.
5. Wire services at an application composition root rather than in routes, views, repositories, or writers.
6. Keep core contracts independent of SQLite, PostgreSQL, Supabase, FastAPI, and Streamlit details.
7. Prevent secrets, paths, credentials, and raw configuration values from leaking through serialization, logs, or errors.
8. Preserve existing GET-only API payloads and read-only Streamlit behavior.

## 3. Non-Goals

- Implementing `src/platform_runtime/` during planning.
- Adding PostgreSQL, Supabase, Auth0, OAuth/OIDC, or other external adapters.
- Adding dependencies, migrations, endpoints, public mutations, upload processing, or UI behavior.
- Making current authenticated or production placeholders deployment-ready.
- Adding tenant/user administration, sessions, MFA, SSO, or token verification.
- Changing Document State, Query Facade, lifecycle, writer, API, or Streamlit public contracts.
- Modifying legacy `src/api/app.py`, root `dashboard.py`, or competitor-price modules.

## 4. Current State

- `compose_document_state(PersistenceConfig)` explicitly selects `in_memory` or file-backed `sqlite` and never falls back.
- `future_postgres` exists only as a rejected deferred backend value.
- `DocumentStateQueryFacadeAdapter` maps injected Document State reads into `WorkflowQueryFacadePort` read models.
- `FacadeDocumentIntelligenceProvider` maps a Query Facade port into existing API payload shapes.
- API routes currently import a module-level deterministic facade provider; the app factory injects auth configuration and identity provider only.
- `LifecycleAdvancementService` receives narrow document reader/writer ports.
- All four Document State writers receive repository surfaces and optionally a lifecycle service.
- API auth modes are `disabled`, `local_demo`, `authenticated`, and `production`.
- `LocalIdentityProvider` is explicit and rejects production use.
- Streamlit supports `local_preview` and `api_preview`; it is read-only and non-authoritative.

## 5. Package Decision

Use a new outer package:

```text
src/platform_runtime/
  __init__.py
  modes.py
  config.py
  errors.py
  contracts.py
  validation.py
  document_state.py
  security.py
  api.py
  composition.py
```

This package is the correct location because it owns application assembly across existing boundaries. It is not part of Workflow Runtime, Document State, API, UI, or security policy. Those packages must never import `platform_runtime`.

- `modes.py`: fixed runtime-mode vocabulary.
- `config.py`: immutable, safe configuration and explicit mapping loader.
- `errors.py`: bounded startup/configuration errors.
- `contracts.py`: immutable composition outputs and service bundles.
- `validation.py`: pure compatibility matrix and fail-closed validation.
- `document_state.py`: constructs Document State, lifecycle, writers, and Query Facade adapter.
- `security.py`: maps runtime config to API auth config and injected identity provider requirements.
- `api.py`: creates API provider/app from composed Query Facade and security dependencies.
- `composition.py`: top-level deterministic orchestration only.

No module performs work at import time or mutates environment variables.

## 6. Runtime Mode Model

Recommended fixed modes:

- `local`: normal developer use; explicit local compatibility defaults are allowed after the mode itself is selected.
- `test`: deterministic test composition; configuration is passed directly, not read implicitly from process environment.
- `demo`: deterministic API-auth demonstration using local-demo identities.
- `local_api_auth`: developer API composition with local-demo authorization enabled.
- `pilot`: persistent single-tenant/pre-production composition requiring non-local authentication.
- `production`: fully fail-closed production composition requiring implemented production persistence and identity adapters.

Unknown modes reject. Modes are not inferred from hostname, debug flags, Streamlit state, branch name, or presence of secrets.

## 7. Runtime Mode Matrix

| Runtime mode | Allowed backends | Required auth | Local identity | API auth disabled | Streamlit `local_preview` | Activation in initial v0.16 |
| --- | --- | --- | --- | --- | --- | --- |
| `local` | `in_memory`; explicit-path `sqlite` | `disabled` or `local_demo` | Allowed only when selected | Allowed | Allowed | Available |
| `test` | `in_memory`; temp file-backed `sqlite` | `disabled` or `local_demo` | Allowed only by fixture/config | Allowed | Allowed | Available |
| `demo` | explicit `in_memory` or explicit-path `sqlite` | `local_demo` | Required deterministic demo provider | No | No; use API preview | Available |
| `local_api_auth` | explicit `in_memory` or explicit-path `sqlite` | `local_demo` | Required deterministic local provider | No | No; use API preview | Available |
| `pilot` | explicit-path `sqlite` | `authenticated` | Forbidden | No | Forbidden | Blocked until a real provider is injected and pilot tenancy limits are approved |
| `production` | implemented production PostgreSQL adapter only | `production` | Forbidden | No | Forbidden | Deliberately unavailable until production adapters exist |

`demo` may use in-memory state only when the ephemeral nature is explicit in safe startup output. It must never be presented as durable. `pilot` is limited to explicitly approved single-tenant operation until child-record tenant columns and cross-record tenant validation are complete.

## 8. Backend And Auth Compatibility Matrix

| Backend | `disabled` | `local_demo` | `authenticated` | `production` |
| --- | --- | --- | --- | --- |
| `in_memory` | Local/test only | Local/test/demo/local-api-auth | Reject | Reject |
| `sqlite` | Local/test only | Local/test/demo/local-api-auth | Pilot only with injected provider | Reject |
| `future_postgres` | Reject | Reject | Reject until implemented | Required for production after implementation |

Additional rules:

- SQLite always requires an explicit file-backed path and never accepts `:memory:`.
- `future_postgres` always rejects until a concrete adapter is implemented and separately approved.
- Authenticated/production auth requires an injected non-local `IdentityProvider`.
- Local-demo auth requires an explicit `LocalIdentityProvider` and is rejected in pilot/production.
- Cross-tenant platform-admin support remains disabled unless separately enabled and audited.

## 9. Configuration Model

Define an immutable `RuntimeConfig` containing only normalized operational choices:

- runtime mode
- Document State backend
- SQLite path configuration, represented safely outside serialization
- API auth mode
- identity-provider kind/reference
- cross-tenant enablement flag, default false
- Streamlit provider mode
- lifecycle truth requirement
- writer activation flag
- safe deployment label and optional bounded feature flags

Configuration loading should use an explicit `Mapping[str, str]` supplied by the entrypoint. Importing the package must not call `os.getenv`, alter `os.environ`, load `.env`, inspect files, or contact a service. A thin executable entrypoint may pass a snapshot of an allowlisted environment mapping into the pure loader.

Recommended allowlisted keys:

- `IDP_RUNTIME_MODE`
- `IDP_DOCUMENT_STATE_BACKEND`
- `IDP_SQLITE_PATH`
- `IDP_API_AUTH_MODE`
- `IDP_IDENTITY_PROVIDER`
- `IDP_ALLOW_CROSS_TENANT`
- `IDP_STREAMLIT_PROVIDER_MODE`
- secret-reference keys approved by a future provider adapter

Config serialization returns only safe choices and booleans such as `sqlite_path_configured`; it never returns a full storage path, secret value, token, credential, DSN, or raw environment mapping.

## 10. Secrets And Configuration Safety

- Secrets are resolved by an injected future `SecretResolver` port at the outermost adapter boundary.
- Core config stores secret references, never secret values.
- `repr`, `str`, `to_dict`, errors, logs, health responses, and Streamlit views must redact secret references and paths.
- Unknown environment keys are ignored only by an explicitly allowlisted loader; unknown required values reject.
- Production and pilot reject unresolved required references.
- No secret may select a runtime mode merely by being present.
- No fallback from malformed production config to local/demo/test config is permitted.

## 11. Composition Contracts

Proposed immutable aggregate contracts:

- `RuntimeComposition`: safe mode descriptor plus composed service bundles.
- `DocumentStateRuntime`: `DocumentStateComposition`, `LifecycleAdvancementService`, writer bundle, and Query Facade port.
- `WriterServices`: ingestion, processing, review, and workflow writers.
- `SecurityRuntime`: API auth config, identity-provider port, and guard.
- `APIRuntime`: `FacadeDocumentIntelligenceProvider` and FastAPI app/application factory result.
- `RuntimeDescriptor`: serialization-safe mode/backend/auth/capability summary for diagnostics.

Concrete repositories, secrets, and internal configuration values must not be serialized by these contracts.

## 12. Composition Flow

```text
Explicit config mapping
  -> RuntimeConfig normalization
  -> compatibility/fail-closed validation
  -> DocumentStateComposition
  -> LifecycleAdvancementService
  -> writer service bundle
  -> DocumentStateQueryFacadeAdapter
  -> WorkflowQueryFacadePort
  -> FacadeDocumentIntelligenceProvider
  -> API auth config + IdentityProvider + PermissionGuard
  -> Document Intelligence API app
  -> Streamlit local_preview or api_preview consumer
```

Construction is all-or-nothing. If a required component fails, no partially composed runtime is returned.

## 13. Document State And Query Facade Wiring

1. Validate backend compatibility before opening SQLite.
2. Call existing `compose_document_state` with explicit `PersistenceConfig`.
3. Create `LifecycleAdvancementService` from the composed document read/write ports.
4. Create all writer services from the shared read/write surfaces and lifecycle service.
5. Create `DocumentStateQueryFacadeAdapter` from the read surface and an injected deterministic clock/snapshot timestamp.
6. Expose it only through `WorkflowQueryFacadePort`.

Query Facade never selects persistence. Document State never imports Query Facade, API, security, UI, or `platform_runtime`.

## 14. Lifecycle And Writer Wiring

- When lifecycle truth is required, all four writers receive the same composed `LifecycleAdvancementService`.
- Writer composition without lifecycle advancement rejects for demo, local-api-auth, pilot, and production.
- A compatibility option without lifecycle injection may remain only for targeted legacy/local tests and must be explicit.
- Writers receive repository ports; they never construct repositories or select backends.
- Future security-aware command gateways remain separate from deterministic writer services.

## 15. API Composition Impact

The API app factory should eventually accept a composed provider dependency in addition to existing auth config and identity provider. Routes should obtain that provider from application state or a narrow FastAPI dependency, not import a module-level provider singleton.

Required compatibility:

- Existing route paths, GET-only methods, envelopes, payload meanings, request IDs, and security headers remain unchanged.
- The current deterministic provider remains available only through explicit local/test compatibility composition.
- Production/pilot cannot use the module-level in-memory provider.
- Auth-enabled API composition requires tenant-aware Query Facade support.
- API construction receives `FacadeDocumentIntelligenceProvider(composed_query_facade)` and validated security dependencies from `platform_runtime`; routes do not select either.

## 16. Streamlit Runtime Selection

- Streamlit remains a consumer and never imports `platform_runtime` service internals, repositories, Query Facade internals, or security policy.
- `local_preview` is allowed only in local/test modes.
- Demo, local-api-auth, pilot, and production use `api_preview`.
- Streamlit may display a safe `RuntimeDescriptor`, but cannot broaden mode, backend, tenant, identity, or permissions.
- Local-demo identity controls remain development-only and are hidden/rejected outside local-demo auth composition.
- API unavailability never causes silent fallback from `api_preview` to local fixtures.

## 17. Production Fail-Closed Rules

Reject startup for:

- production plus `in_memory` or SQLite
- production plus disabled/local-demo/authenticated-placeholder auth
- production plus local identity provider
- production without an implemented persistent production backend
- production/pilot with missing identity provider or unresolved required secret reference
- authenticated mode without a non-local provider
- SQLite without an explicit file path
- deferred `future_postgres` before implementation
- writers without lifecycle advancement when lifecycle truth is required
- guarded API without tenant-aware Query Facade/provider support
- Streamlit `local_preview` in demo, local-api-auth, pilot, or production
- any unknown mode/backend/auth/provider combination

Errors contain stable codes and safe field names only. They do not echo values, secrets, paths, DSNs, claims, or exceptions.

## 18. Boundary Rules

- `platform_runtime` may import public boundaries from Document State, Query Facade, API, security, lifecycle, and writers.
- No core/runtime/UI/API package imports `platform_runtime` back.
- Security imports no API, Document State, Query Facade, UI, persistence, or platform composition.
- Document State imports no API, security, UI, or platform composition.
- Query Facade selects no backend and imports no persistence implementation.
- API routes select no provider, backend, writer, or identity implementation.
- Streamlit remains API/local-display only and imports no repositories or writer services.
- Future PostgreSQL/Supabase adapters live at outer adapter boundaries and map inward to existing ports.

## 19. Testing Strategy

- Immutable config and safe serialization tests.
- Complete mode/backend/auth/identity/Streamlit compatibility matrix tests.
- Local, test, demo, and local-api-auth composition tests.
- Pilot and production fail-closed tests.
- No implicit local identities or in-memory backend in production.
- SQLite explicit-path and no-fallback tests.
- Deferred PostgreSQL rejection tests.
- Query Facade read-through from selected in-memory/SQLite backend.
- Writer bundle identity and lifecycle-service injection tests.
- API provider/app receives composed Query Facade and auth dependencies.
- Existing API paths/payloads and Streamlit behavior regression tests.
- Secret/path redaction tests for config, errors, descriptors, and logs.
- Recursive boundary/import checks and import-time side-effect checks.
- Full regression and generated-file hygiene verification.

## 20. Proposed Implementation Phases

1. Runtime mode/config contracts and validation matrix.
2. Composition root for Document State, Query Facade, lifecycle, and writers.
3. API app/provider/auth composition activation.
4. Streamlit runtime selection/config preview.
5. Production fail-closed verification and boundary hardening.
6. Release closure, handoff, and owner tag recommendation.

Phase 1 delivered the standard-library-only `src/platform_runtime/` contract package with fixed runtime, backend, auth, identity-provider, API exposure, and Streamlit mode catalogs; immutable nested configuration; redacted JSON-safe projection; stable privacy-safe validation errors/results; pure compatibility helpers; and deterministic fail-closed matrix validation. It performs no environment reads, resource construction, service composition, API integration, Streamlit integration, or external-provider activation.

Phase 2 delivers the internal runtime composition root. It validates configuration before construction, explicitly selects in-memory or file-backed SQLite Document State with no fallback, composes one lifecycle advancement service, injects it into all four writer services, and exposes a Document State-backed Workflow Query Facade using an explicit snapshot timestamp. The frozen result provides a redacted safe summary and ownership hook. API app creation, auth/provider activation, Streamlit behavior, production persistence, and external providers remain unchanged and deferred.

Phase 3 activates that composition at the API-owned application boundary. The app factory accepts either validated `RuntimeConfig` or an existing `RuntimeComposition`, installs a facade-backed provider and mapped auth composition on `app.state`, and registers the runtime cleanup hook. Routers resolve the app-scoped provider while retaining the existing singleton only for default compatibility. Disabled and local-demo auth are supported; authenticated and production placeholders reject before runtime construction. Paths, methods, envelopes, payload meanings, tenant narrowing, request IDs, and security headers remain unchanged. Streamlit remains untouched.

Phase 4 adds non-authoritative runtime preview labels to Streamlit `api_preview`. Fixed local/test/demo/local-API-auth, API-default/in-memory/SQLite, and disabled/local-demo labels are display-only; they never construct services, select persistence, decide tenant scope, or enforce permissions. Existing API URL and allowlisted local-demo identity controls remain unchanged. Runtime, auth, unavailable, forbidden, concealed-not-found, and malformed-response states map to fixed operator-safe messages. `local_preview` remains the unchanged default.

## 21. Deferred Work

- PostgreSQL/Supabase repositories and production migrations.
- Real identity-provider and secret-manager adapters.
- Token verification, sessions, MFA, SSO, and user/tenant administration.
- Child-record tenant columns and cross-record tenant validation.
- Public mutations, upload API/UI, and security-aware writer command gateway.
- Production telemetry, health/readiness orchestration, process supervision, and deployment manifests.
- Backup/recovery, retention, legal hold, and encrypted raw blob storage.
- FlowSync Document Intelligence authentication and production UI.

## 22. Risks And Open Questions

- The API currently uses module-level provider imports; Phase 3 needs dependency injection without route or payload drift.
- Production cannot compose until a durable production backend and real identity provider exist. This is intentional.
- Pilot mode needs an owner decision on single-tenant limitations while child records lack tenant columns.
- A future secret resolver interface and deployment-specific implementation need separate approval.
- Snapshot clock ownership for Query Facade composition must be explicit and deterministic in tests.
- Shutdown/close ownership for SQLite and future providers needs a lifecycle contract.
- Compatibility entrypoints must be clearly labeled so production cannot accidentally invoke them.

## 23. Acceptance Criteria

- Package location and one-way dependency direction are approved.
- Runtime mode, backend, auth, identity, and Streamlit matrices are explicit.
- Production has no implicit defaults and rejects unsupported dependencies.
- Local/test behavior remains deterministic and backward compatible.
- Document State, lifecycle, writers, Query Facade, API provider, auth, and app construction have a single documented order.
- API routes and Streamlit remain non-authoritative consumers.
- Secrets and storage paths cannot appear in safe config, errors, or descriptors.
- Implementation is split into six narrow, independently verifiable phases.
- No code, tests, endpoints, migrations, dependencies, or UI behavior change during planning.
