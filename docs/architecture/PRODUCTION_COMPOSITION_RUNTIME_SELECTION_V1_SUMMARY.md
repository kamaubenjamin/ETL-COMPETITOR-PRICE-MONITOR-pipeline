# Production Composition / Runtime Selection v1 Summary

**Milestone:** v0.16
**Status:** Implemented and verified; closed pending owner tag

## Milestone Purpose

v0.16 establishes one explicit outer composition boundary for selecting and wiring the platform's runtime mode, Document State backend, lifecycle service, internal writers, Workflow Query Facade, API provider, and API authorization dependencies. It preserves deterministic local operation while making unsupported pilot and production combinations fail closed.

Closure does not make production deployment available. PostgreSQL/Supabase persistence, a real identity provider, token verification, secret resolution, and deployment infrastructure remain deferred.

## Delivered Capabilities

- Fixed `RuntimeMode`, `BackendMode`, and `AuthMode` catalogs.
- Immutable `RuntimeConfig` contracts with pure normalization and validation.
- Redacted JSON-compatible configuration and runtime summaries.
- A deterministic backend/auth/identity/Streamlit compatibility matrix.
- Production fail-closed validation with stable privacy-safe errors.
- `src/platform_runtime/` as the outer composition root.
- Explicit in-memory or file-backed SQLite Document State selection with no fallback.
- One composed `LifecycleAdvancementService` shared by the writer bundle.
- Composed ingestion, processing, review, and workflow writer services.
- `DocumentStateQueryFacadeAdapter` exposed through the Workflow Query Facade port.
- App-scoped API provider and authorization composition.
- Display-only Streamlit runtime/backend/auth preview labels.
- Recursive boundary, provider-isolation, privacy, and startup-failure verification.

## Phase Summary

1. **Runtime contracts:** Added mode catalogs, immutable configuration, redacted serialization, safe errors, and the fail-closed validation matrix.
2. **Internal composition:** Wired Document State, lifecycle advancement, all four writers, and Query Facade behind one validated composition.
3. **API activation:** Added runtime-config and precomposed-runtime app construction with app-scoped provider/auth dependencies and preserved compatibility defaults.
4. **Streamlit preview:** Added non-authoritative display labels and fixed safe runtime error states without service construction or local enforcement.
5. **Production hardening:** Verified invalid production and deferred combinations reject before resources or FastAPI construction and tightened one-way boundaries.
6. **Release closure:** Re-ran focused and full verification and completed summary, handoff, release, roadmap, debt, ADR, and changelog documentation.

## Runtime Architecture

```text
RuntimeConfig
  -> validate_runtime_config
  -> RuntimeComposition
  -> DocumentStateComposition
  -> LifecycleAdvancementService
  -> RuntimeWriterServices
  -> DocumentStateQueryFacadeAdapter
  -> WorkflowQueryFacadePort
  -> FacadeDocumentIntelligenceProvider
  -> Document Intelligence API
  -> Streamlit api_preview consumer
```

`platform_runtime` owns assembly only. Domain services retain their existing responsibilities and do not import the composition package.

## Supported Modes

- Runtime modes: `local`, `test`, `demo`, `local_api_auth`, `pilot`, and `production`.
- Backend modes: `in_memory`, `sqlite`, and deferred `future_postgres`.
- Auth modes: `disabled`, `local_demo`, `authenticated`, and `production`.

Currently usable combinations are deterministic local/test in-memory or explicit SQLite, demo with an explicit backend and local-demo auth, and local API auth with an explicit backend and local-demo auth. Pilot requires explicit SQLite and a real injected non-local identity provider. Production remains unavailable because no production persistence or identity adapter exists.

## Fail-Closed Rules

The runtime rejects production with in-memory or SQLite persistence, disabled/local-demo/authenticated-placeholder auth, a local identity, or deferred PostgreSQL. It also rejects deferred PostgreSQL in every mode, SQLite without an explicit file path, invalid caller-supplied compositions, API construction from invalid config, and attempts to treat Streamlit as a production selector. Rejection never falls back to local configuration or the compatibility provider.

## API And Streamlit Compatibility

- Existing endpoint paths, GET-only methods, payload meanings, envelopes, pagination, request IDs, and security headers are unchanged.
- Default app creation and the deterministic provider singleton remain intentionally available for local compatibility.
- Runtime-composed apps use app-scoped providers and validated auth composition.
- Streamlit `local_preview` remains unchanged and default.
- `api_preview` runtime labels are display-only; Streamlit does not construct services, select persistence, authorize users, or decide tenant scope.

## Privacy And Boundaries

Safe summaries and errors exclude SQLite paths, identity-provider references, tokens, credentials, raw environment values, storage paths, stack traces, and raw exceptions. Core packages do not import `platform_runtime`; the composition package may import only approved public boundaries. API access is limited to approved app/auth/config entrypoints, and Streamlit remains consumer-only.

## Verification Results

- Platform Runtime: 84 passed.
- Document Intelligence API: 80 passed, 9 skipped.
- Streamlit UI: 64 passed.
- Security: 60 passed.
- Document State: 330 passed.
- Workflow Query Facade and Review Runtime: 239 passed.
- Full regression: 1,535 passed, 9 skipped, 712 warnings.
- Runtime boundary verification: compliant, with two pre-existing U+FEFF scan warnings.
- Python compilation and `git diff --check`: passed.

## Deferred Work

- PostgreSQL/Supabase repository and production migration adapters.
- Real identity-provider, token-verification, and secret-resolver adapters.
- Production deployment, gateway/TLS, diagnostics, telemetry, backup, and recovery.
- Resource shutdown ownership beyond current no-op/local cleanup.
- Child-record tenancy and a security-aware writer authorization gateway.
- Public upload/mutation APIs and ERP/export permissions.
- FlowSync Document Intelligence runtime and authentication integration.
