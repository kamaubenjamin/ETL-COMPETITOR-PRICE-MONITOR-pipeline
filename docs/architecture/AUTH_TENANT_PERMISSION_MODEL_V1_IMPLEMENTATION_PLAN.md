# Auth, Tenant, And Permission Model v1 Implementation Plan

**Milestone:** v0.15
**Status:** Phases 1-4 implemented; Phase 5 not started

## 1. Milestone Overview

v0.15 introduces a provider-neutral, default-deny security boundary while preserving the current read-only local platform. Implementation is split into five independently reviewable phases. Each phase must stop after its own tests and documentation updates.

No phase may hard-code Supabase, add public mutation endpoints, let API routes implement role logic inline, let Streamlit bypass API authorization, or let writers authenticate users.

## 2. Global Boundary Requirements

- `src/security/` owns identity and authorization contracts/policy.
- Core security imports only standard library and package-local modules.
- Identity-provider adapters depend inward on security contracts; core security never imports adapters.
- API uses guards/context but does not embed permission algorithms in routes.
- Document State stores and filters tenant/actor fields but does not evaluate roles.
- Query Facade applies an authorized tenant read scope but does not authenticate or decide permissions.
- Writers receive authorized attribution and tenant scope; they do not resolve identity or roles.
- Streamlit remains an API consumer in authenticated modes.
- Legacy API/dashboard and competitor-price modules remain outside v0.15.

## 3. Phase 1: Security Contracts And Role Catalog

### Objectives

- Create immutable provider-neutral contracts for `Principal`, `Tenant`, role bindings, permissions, `ResourceScope`, `AuthorizationContext`, `AuthorizationDecision`, `PolicyResult`, and actor attribution.
- Create fixed permission and role catalogs.
- Define user, service-account, and system identities.
- Add privacy-safe errors and deterministic pure policy evaluation.

### Expected Files

Create:

- `src/security/__init__.py`
- `src/security/contracts.py`
- `src/security/principals.py`
- `src/security/permissions.py`
- `src/security/roles.py`
- `src/security/decisions.py`
- `src/security/context.py`
- `src/security/errors.py`
- `src/security/policies.py`
- `tests/security/test_principals.py`
- `tests/security/test_permissions_roles.py`
- `tests/security/test_authorization_context.py`
- `tests/security/test_policy_catalog.py`
- `tests/security/test_security_privacy.py`
- `tests/security/test_security_boundaries.py`

Modify only v0.15 status documentation as needed.

### Required Tests

- Contracts are immutable and JSON-compatible.
- IDs, tenant memberships, roles, permissions, and metadata are bounded.
- Role-to-permission mappings are deterministic.
- Unknown roles/permissions reject.
- Service and system principals are explicit.
- Anonymous, user, service-account, and system principals are explicit and deterministic.
- Tokens, credentials, raw claims, and unsafe metadata reject.
- Forbidden imports and external dependencies are absent.

### Verification

```text
python -m pytest tests/security -q
python scripts/verify_boundaries.py
python -m py_compile src/security/contracts.py
python -m py_compile src/security/principals.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after contracts, catalogs, context, pure policy, privacy, and boundary tests. Do not add identity-provider adapters, guards, persistence fields, API integration, or UI changes.

**Completion:** Implemented and verified. The pure policy evaluator was included to make default-deny and tenant-scope semantics executable; provider adapters and enforcement guards remain Phase 2 work.

## 4. Phase 2: Policy Engine And Permission Guards

### Objectives

- Implement pure default-deny policy evaluation.
- Build request/internal authorization contexts from verified principals.
- Implement reusable `PermissionGuard` behavior.
- Enforce tenant memberships, explicit cross-tenant administration, and service-account scopes.

### Expected Files

Create:

- `src/security/providers/__init__.py`
- `src/security/providers/contracts.py`
- `src/security/providers/local.py`
- `src/security/guards.py`
- `src/security/requests.py`
- `tests/security/test_identity_provider_contracts.py`
- `tests/security/test_local_identity_provider.py`
- `tests/security/test_authorization_guards.py`
- `tests/security/test_authorization_requests.py`
- `tests/security/test_phase2_boundaries.py`

Modify Phase 1 exports and obsolete Phase 1 stop-condition tests only as needed.

### Required Tests

- Missing identity denies in authenticated mode.
- Role-derived permission allows and denies are deterministic.
- Active tenant must be an allowed membership.
- Client tenant selection cannot broaden scope.
- Platform-admin cross-tenant access requires explicit enablement and audit flag.
- Service accounts require explicit tenant and permissions.
- System actors cannot be supplied by an untrusted request.
- Errors and decisions remain privacy-safe.
- Context does not leak between concurrent requests/tasks.

### Verification

```text
python -m pytest tests/security -q
python scripts/verify_boundaries.py
python -m py_compile src/security/context.py
python -m py_compile src/security/policies.py
python -m py_compile src/security/guards.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after pure policy and guard verification. Do not modify Document State, Query Facade, API, UI, or writers.

**Completion:** Implemented and verified. Local identities remain explicit demo/test fixtures and cannot select production mode; no consumer, repository, writer, migration, or external-provider integration was added.

## 5. Phase 3: Tenant-Aware Document State And Query Facade Contracts

### Objectives

- Add versioned tenant/ownership/attribution contracts without embedding authorization logic.
- Define mandatory tenant-scoped repository and Query Facade reads for authenticated composition.
- Preserve current local-preview contracts through explicit compatibility adapters.
- Add migration artifacts only when this implementation phase is separately approved.

### Expected Areas

- `src/document_state/` records, queries, repository ports, in-memory backend, SQLite schema/migrations/mappers/repositories, and composition.
- `src/workflow_runtime/query_facade/` tenant read-scope contracts and ports.
- `src/document_state/adapters/query_facade_adapter.py` tenant propagation.
- Corresponding Document State, persistence, Query Facade, and boundary tests.

Exact files must be confirmed by a Phase 3 inspection before editing.

### Required Behavior

- Tenant identity is an explicit relational/contract field, not metadata.
- Child records carry tenant scope and cannot reference cross-tenant parents.
- Repository get/list/count/pagination operations require or receive trusted tenant scope in secured composition.
- Stable IDs and idempotency cannot collide across tenant boundaries.
- Query Facade applies tenant filtering to every read family.
- Existing API payloads do not automatically expose tenant/ownership fields.
- Legacy data has a deterministic local-tenant backfill strategy.

### Required Tests

- In-memory/SQLite tenant conformance.
- Cross-tenant get/list/write denial.
- Tenant-filtered counts and pagination.
- Cross-tenant relationship rejection.
- Local legacy backfill/reconstruction.
- No security policy in repositories or Query Facade.
- API/UI do not import repositories directly.

### Verification

```text
python -m pytest tests/security tests/document_state tests/workflow_runtime/query_facade -q
python -m pytest tests/api/document_intelligence tests/ui/streamlit tests/review_runtime -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after tenant-aware storage/read contracts and conformance. Do not wire API guards, Streamlit auth, public mutations, or external identity providers.

**Completion:** Implemented and verified for the document projection boundary. `DocumentRecord`, in-memory/SQLite document reads, and Query Facade document reads support optional tenant narrowing; migration `002` preserves legacy rows as `tenant-local`; API document payloads remain unchanged. Child-record tenant columns, cross-record tenant validation, and authenticated enforcement are deferred to Phase 4 or a separately approved expansion.

## 6. Phase 4: Read-Only Consumer Guards And Writer Attribution Boundary

### Objectives

- Add opt-in Document Intelligence API identity/context/guard composition for existing GET routes.
- Keep route permission declarations thin and reusable.
- Pass authorized tenant scope to the API provider/Query Facade path.
- Add Streamlit mode planning/adapter support without client-side authority.
- Define and verify a security-aware internal command gateway and actor attribution; do not add public writes.

### Expected Areas

- API security adapter/dependencies and composition modules under `src/api/document_intelligence/`.
- API provider authorization wrapper, without payload changes.
- Streamlit API client/provider configuration for authenticated mode, without repository access.
- Security command-gateway/attribution contracts and writer tests.
- Existing API, Streamlit, writer, audit, and boundary tests.

Exact files require Phase 4 inspection. Legacy `src/api/app.py` and root `dashboard.py` remain untouched.

### Required Behavior

- Existing local preview remains explicit and deterministic.
- Production/authenticated mode denies missing identity and tenant scope.
- API routes declare permissions but contain no role/tenant algorithms.
- List/get reads use only guard-produced tenant scope.
- Safe `401`, `403`, and tenant-hiding `404` envelopes preserve request IDs and headers.
- Streamlit authenticated mode uses API only and has no silent local fallback.
- Writer gateway authorizes before constructing trusted tenant/actor attribution.
- No POST/PUT/PATCH/DELETE route is added.

### Required Tests

- Every existing route has a declared read permission.
- Missing/invalid identity and tenant mismatch fail safely.
- Tenant-scoped API data never crosses scope.
- Platform-admin cross-tenant path is explicit and audited.
- Streamlit local mode remains compatible; authenticated mode cannot bypass API.
- Writer attribution and audit actor/tenant fields derive from trusted context.
- Existing v0.9 payload meanings, envelopes, security headers, and GET-only methods remain unchanged.

### Verification

```text
python -m pytest tests/security tests/api/document_intelligence tests/ui/streamlit -q
python -m pytest tests/document_state tests/workflow_runtime/query_facade tests/review_runtime -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after opt-in read authorization and internal attribution verification. Do not add external providers, public mutations, or production activation.

**Completion:** Implemented and verified for API read guards only, following the separately approved Phase 4 scope. Existing GET routes declare centralized permissions, auth-enabled reads receive a guard-produced tenant scope, cross-tenant resource reads are concealed, and auth-disabled local preview remains unchanged. Streamlit authentication and writer attribution/enforcement remain deferred; no public mutation or production identity provider was added.

## 7. Phase 5: Security Verification, Documentation, And Release Closure

### Objectives

- Verify tenant isolation and no-bypass boundaries end to end.
- Run focused and full regressions.
- Document local versus authenticated modes, migration state, limitations, and provider adapter rules.
- Create summary, handoff, release notes, and owner tag recommendation.

### Expected Files

Create:

- `docs/architecture/AUTH_TENANT_PERMISSION_MODEL_V1_SUMMARY.md`
- `docs/architecture/AUTH_TENANT_PERMISSION_MODEL_V1_HANDOFF.md`
- `docs/releases/v0.15-auth-tenant-permissions.md`

Modify:

- both v0.15 plans
- ADR-020
- `docs/ROADMAP.md`
- `TECHNICAL_DEBT.md`
- `CHANGELOG.md`

### Required Verification

- Security, Document State, Query Facade, API, Streamlit, writers, lifecycle, Review Runtime, and boundary suites.
- Full regression.
- Recursive forbidden-import checks.
- Route guard inventory and GET-only verification.
- Tenant isolation/privacy matrix for list/get/pagination/audit/writer paths.
- `git diff --check` and clean generated-file review.

### Stop Condition

Stop after release documentation and verification. Do not commit, push, or tag unless explicitly instructed.

## 8. Backward Compatibility Requirements

- Keep `local_preview` available under explicit local/test configuration.
- Keep current local `api_preview` during migration; production composition must fail closed.
- Preserve v0.9 paths, GET-only methods, payload meanings, envelopes, request IDs, and headers.
- Preserve existing Document State and Query Facade behavior through explicit compatibility adapters until tenant-aware versions are activated.
- Do not silently assign tenant scope from arbitrary request values.
- Do not activate auth or tenant migrations automatically.

## 9. Migration And Rollout Rules

1. Add security contracts and guards without runtime activation.
2. Add tenant-aware storage/read versions and deterministic local-data backfill.
3. Run dual-path compatibility tests, not silent fallback.
4. Enable authenticated local/dev API composition explicitly.
5. Add a real identity-provider adapter in a later milestone.
6. Require real identity and mandatory tenant scope before production mode can start.
7. Retire unscoped production paths only after data migration and parity verification.

## 10. Risks And Mitigations

- Tenant leakage: mandatory scope and negative integration tests.
- Route drift: centralized guard dependency plus route inventory tests.
- Role coupling: policies consume permissions, not role names.
- Local bypass: explicit modes and production fail-closed configuration.
- Provider lock-in: provider adapters map inward to stable contracts.
- Migration breakage: versioned contracts and deterministic legacy-tenant backfill.
- Writer spoofing: trusted gateway creates actor attribution; command payload cannot self-authorize.
- Audit overexposure: separate `audit:read`, tenant filtering, and safe metadata.

## 11. Definition Of Done

- Provider-neutral security contracts and fixed role/permission catalog exist.
- Default-deny tenant policy and guards are deterministic and tested.
- Secured Document State/Query Facade paths require tenant scope.
- Existing read-only API routes are guarded without inline permission logic or payload changes.
- Streamlit authenticated mode cannot bypass API; local preview remains explicit.
- Writers remain authentication-free and use trusted attribution boundaries.
- Actor and tenant audit attribution is privacy-safe.
- In-memory/SQLite and local/authenticated compatibility tests pass.
- Supabase/PostgreSQL remain deferred adapters with no core dependency.
- Full regression and boundary verification pass.
- Release summary, handoff, notes, roadmap, debt, changelog, and ADR are complete.

## 12. Commit And Tag Strategy

Recommended owner-reviewed phase commits:

1. `feat: add security identity and permission contracts`
2. `feat: add tenant authorization policies and guards`
3. `feat: add tenant-aware document state read boundaries`
4. `feat: guard document intelligence reads and writer attribution`
5. `chore: close v0.15 auth tenant permissions`

Recommended tag after closure verification:

`v0.15-auth-tenant-permissions`
