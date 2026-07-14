# Production Composition / Runtime Selection v1 Implementation Plan

**Milestone:** v0.16
**Status:** Planned; implementation not started

## 1. Milestone Overview

Implement one explicit outer composition layer under `src/platform_runtime/`. Each phase must preserve current public contracts, fail closed for invalid combinations, and stop before the next phase. Production remains deliberately non-startable until a real production persistence adapter and identity provider are separately approved.

## 2. Global Requirements

- No implicit runtime-mode selection.
- No environment reads or side effects at module import.
- No fallback between persistence or identity providers.
- No production use of in-memory, SQLite, local identities, or disabled auth.
- No provider/backend selection inside routes, views, Query Facade, repositories, lifecycle services, or writers.
- No secrets, credentials, claims, DSNs, paths, or raw exceptions in serialization/errors.
- Preserve existing API paths, GET-only methods, payloads, envelopes, and Streamlit behavior.
- Keep legacy `src/api/app.py`, root `dashboard.py`, and competitor-price modules untouched.

## 3. Phase 1: Runtime Mode, Config Contracts, And Validation Matrix

### Scope

Create dependency-light composition contracts only.

### Expected Files

Create:

- `src/platform_runtime/__init__.py`
- `src/platform_runtime/modes.py`
- `src/platform_runtime/config.py`
- `src/platform_runtime/errors.py`
- `src/platform_runtime/contracts.py`
- `src/platform_runtime/validation.py`
- `tests/platform_runtime/__init__.py`
- `tests/platform_runtime/test_config.py`
- `tests/platform_runtime/test_validation.py`
- `tests/platform_runtime/test_boundaries.py`

Modify documentation only as needed for verified design deviations.

### Required Behavior

- Define fixed runtime/backend/auth/identity/Streamlit mode values.
- Define immutable `RuntimeConfig`, safe `RuntimeDescriptor`, and composition contract shells.
- Parse only an explicitly supplied mapping with allowlisted keys.
- Validate the complete compatibility matrix before any resource creation.
- Expose stable safe error codes and fields only.
- Redact paths and secret references from `repr`, `str`, and serialization.
- Reject deferred PostgreSQL and every unsafe production combination.

### Tests

- Every matrix combination is allowed or rejected deterministically.
- Unknown/missing values fail safely.
- Production rejects in-memory, SQLite, local identity, disabled auth, and missing providers.
- SQLite requires an explicit file-backed path.
- Config is immutable and JSON-compatible only through safe projection.
- No import-time environment access or mutation.
- No forbidden imports.

### Verification

```text
python -m pytest tests/platform_runtime -q
python scripts/verify_boundaries.py
python -m py_compile src/platform_runtime/config.py
python -m py_compile src/platform_runtime/validation.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after contracts and pure validation. Do not construct repositories, services, API apps, or Streamlit providers.

## 4. Phase 2: Document State, Query Facade, Lifecycle, And Writers

### Scope

Compose existing backend-neutral services from explicit validated config.

### Expected Files

Create:

- `src/platform_runtime/document_state.py`
- `src/platform_runtime/composition.py`
- `tests/platform_runtime/test_document_state_composition.py`
- `tests/platform_runtime/test_writer_lifecycle_composition.py`
- `tests/platform_runtime/test_query_facade_composition.py`

Modify only if a verified public-export gap exists:

- `src/platform_runtime/contracts.py`
- package `__init__.py` exports

### Required Behavior

- Call existing `compose_document_state` with validated backend config.
- Construct one `LifecycleAdvancementService` from composed document ports.
- Construct all four writers from the same repository surfaces and lifecycle service.
- Construct `DocumentStateQueryFacadeAdapter` from the read surface and injected clock/snapshot.
- Return immutable bundles with explicit active backend and capabilities.
- Close resources through an explicit owner/lifecycle contract if required.
- Never silently omit lifecycle advancement where lifecycle truth is required.

### Tests

- Local/test in-memory composition.
- Local/test/demo SQLite composition and reopen behavior.
- Query Facade reads selected repository state.
- Writers share the expected lifecycle service and repository surfaces.
- Invalid config creates no resource.
- Deferred/production backends reject before connection attempts.
- Existing Document State, lifecycle, writer, and Query Facade suites pass.

### Verification

```text
python -m pytest tests/platform_runtime tests/document_state tests/workflow_runtime/query_facade -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after internal service composition. Do not modify API or Streamlit.

## 5. Phase 3: API Provider, App, And Auth Composition Activation

### Scope

Inject the composed Query Facade provider and security dependencies into the Document Intelligence API app.

### Expected Files

Create:

- `src/platform_runtime/security.py`
- `src/platform_runtime/api.py`
- `tests/platform_runtime/test_security_composition.py`
- `tests/platform_runtime/test_api_composition.py`

Modify narrowly:

- `src/api/document_intelligence/app.py`
- API provider dependency boundary/router dependency helper
- existing API tests required for injection compatibility

### Required Behavior

- Create `FacadeDocumentIntelligenceProvider` from the composed `WorkflowQueryFacadePort`.
- Pass validated API auth config and injected identity provider into app creation.
- Replace route dependence on module-level provider singleton with app-scoped/narrow dependency access.
- Keep the current module-level app as explicit local compatibility only.
- Preserve every route, method, payload, envelope, request ID, and security header.
- Reject auth-enabled composition without tenant-aware query support.
- Reject pilot/production without a real non-local provider.

### Tests

- Local disabled-auth compatibility.
- Local-demo guarded API composition.
- Provider reads selected in-memory/SQLite state.
- No provider singleton is used by composed app routes.
- Production/local-provider and authenticated/no-provider combinations reject.
- Existing API and security tests pass unchanged in meaning.

### Verification

```text
python -m pytest tests/platform_runtime tests/api/document_intelligence tests/security -q
python -m pytest tests/document_state tests/workflow_runtime/query_facade -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after API composition activation. Do not add endpoints, mutations, external providers, or Streamlit changes.

## 6. Phase 4: Streamlit Runtime Selection And Safe Config Preview

### Scope

Connect existing Streamlit provider modes to a safe runtime descriptor without making Streamlit authoritative.

### Expected Files

Modify only as required:

- `src/ui/streamlit/document_intelligence_app.py`
- `src/ui/streamlit/data_providers.py`
- `src/ui/streamlit/api_client.py`
- focused Streamlit tests
- `src/platform_runtime/contracts.py` only for a safe consumer descriptor

### Required Behavior

- Preserve `local_preview` as the local/test default.
- Require `api_preview` for demo, local-api-auth, pilot, and production.
- Hide/reject local-demo identity controls outside local-demo auth mode.
- Display only safe mode/backend/auth capability labels.
- Never expose paths, secrets, provider claims, or tenant internals.
- Never fall back from unavailable API to local fixtures.
- Streamlit performs no authorization or backend selection.

### Tests

- Existing local preview remains unchanged.
- Runtime descriptor is safe and display-only.
- Invalid provider/mode combinations reject before rendering data.
- Production/pilot cannot select local preview or local identity.
- Existing Streamlit API-preview and auth-preview tests pass.

### Verification

```text
python -m pytest tests/ui/streamlit tests/platform_runtime -q
python -m pytest tests/api/document_intelligence tests/security -q
python scripts/verify_boundaries.py
python -m py_compile src/ui/streamlit/document_intelligence_app.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after safe mode display/provider selection. Do not add UI writes, login/session flows, or external identity.

## 7. Phase 5: Production Fail-Closed And Boundary Hardening

### Scope

Verify no unsafe combination, fallback, import path, or serialization can bypass the composition root.

### Expected Files

Create if needed:

- `tests/platform_runtime/test_production_fail_closed.py`
- `tests/platform_runtime/test_secret_redaction.py`
- `tests/platform_runtime/test_composition_boundaries.py`
- `tests/platform_runtime/test_runtime_integration.py`

Modify production code only for verified defects.

### Required Verification

- Complete compatibility-matrix coverage.
- Production rejects every local/deferred dependency.
- Pilot rejects missing provider, path, and unsupported multi-tenant activation.
- No implicit environment/config/provider/backend selection.
- No partial composition after failure.
- No secret/path leakage in config, errors, descriptors, or logs.
- API/UI cannot import persistence or writers directly.
- Core packages cannot import `platform_runtime`.
- Full read-after-write-to-API composition works for approved local/test backends.
- Full regression passes.

### Verification

```text
python -m pytest tests/platform_runtime -q
python -m pytest tests/document_state tests/workflow_runtime/query_facade -q
python -m pytest tests/api/document_intelligence tests/ui/streamlit tests/security tests/review_runtime -q
python scripts/verify_boundaries.py
python -m pytest -q
git diff --check
git status --short --branch
```

### Stop Condition

Stop after hardening and verification. Do not implement PostgreSQL, Supabase, public mutations, or deployment infrastructure.

## 8. Phase 6: Release Closure And Handoff

### Expected Files

Create:

- `docs/architecture/PRODUCTION_COMPOSITION_RUNTIME_SELECTION_V1_SUMMARY.md`
- `docs/architecture/PRODUCTION_COMPOSITION_RUNTIME_SELECTION_V1_HANDOFF.md`
- `docs/releases/v0.16-production-composition-runtime-selection.md`

Modify:

- both v0.16 plans
- ADR-021
- `docs/ROADMAP.md`
- `TECHNICAL_DEBT.md`
- `CHANGELOG.md`

### Required Behavior

- Record only capabilities proven by tests.
- Document available and deliberately unavailable modes.
- Document exact startup/configuration and resource ownership rules.
- Preserve production fail-closed claims and deferred adapters.
- Recommend owner tag without creating it.

### Verification

Run focused suites, boundary verification, full regression, `git diff --check`, and generated-file review.

### Stop Condition

Stop after release docs and verification. Do not commit, push, or tag unless explicitly instructed.

## 9. Backward Compatibility Requirements

- Existing direct local/test factories remain available during migration but are explicitly non-production.
- Current API paths, GET-only methods, payload meanings, envelopes, request IDs, and headers remain stable.
- Streamlit `local_preview` and `api_preview` retain current user-visible semantics in allowed modes.
- Existing Document State, Query Facade, lifecycle, and writer constructors remain valid.
- No environment variable becomes mandatory for existing unit tests.

## 10. Risks And Mitigations

- **Partial construction:** validate first; return composition only after every dependency succeeds.
- **Hidden fallback:** exact enum matrix and negative tests; no catch-and-select behavior.
- **Provider singleton bypass:** app-scoped provider dependency and route inventory tests.
- **Production placeholder confusion:** production mode always rejects until concrete adapters are registered.
- **Secret leakage:** safe projection contracts and hostile-value tests.
- **Resource leaks:** explicit close ownership for SQLite/future providers.
- **Circular imports:** outer-layer-only dependency direction and recursive import tests.
- **Local regression:** preserve explicit compatibility entrypoints and run full suite each phase.

## 11. Definition Of Done

- Runtime mode/config contracts and compatibility matrix are implemented and tested.
- One composition root wires Document State, lifecycle, writers, Query Facade, API provider, auth, and app.
- Streamlit consumes safe runtime selection without authority.
- Production and pilot fail closed for missing/unsupported dependencies.
- No implicit in-memory, local identity, disabled auth, SQLite path, or deferred backend selection exists in production.
- Secrets and paths are absent from safe output and errors.
- Boundaries remain compliant and full regression passes.
- Summary, handoff, release notes, roadmap, debt, ADR, and changelog are complete.

## 12. Commit And Tag Strategy

Recommended owner-reviewed commits:

1. `feat: add platform runtime config contracts`
2. `feat: compose document state lifecycle and writers`
3. `feat: inject composed provider and auth into API`
4. `feat: add safe Streamlit runtime selection preview`
5. `test: harden production composition boundaries`
6. `docs: close v0.16 production composition runtime selection`

Recommended tag after Phase 6 owner review:

`v0.16-production-composition-runtime-selection`

