# Auth, Tenant, And Permission Model v1 Plan

**Milestone:** v0.15
**Status:** Implemented and verified; closed pending owner tag

## 1. Problem Statement

The Document Intelligence Platform is currently an intentionally unauthenticated, read-only local foundation. API request context contains a request ID but no verified identity. Streamlit workspaces are display filters, not security boundaries. Document State records and Workflow Query Facade queries have no tenant scope, while selected correction and audit records contain only unverified actor identifiers.

Before production composition, the platform needs a provider-neutral security boundary that authenticates principals, resolves tenant-scoped roles and permissions, produces deterministic authorization decisions, and propagates approved tenant/actor attribution without moving security policy into API routes, UI components, repositories, query logic, or writers.

## 2. Goals

1. Define authentication and authorization as an explicit boundary layer.
2. Define immutable, JSON-compatible principal, tenant, role, permission, scope, context, and decision contracts.
3. Enforce default-deny tenant isolation with no caller-supplied tenant bypass.
4. Keep Document State storage-focused and Query Facade read-focused.
5. Keep writers identity-provider-neutral and unable to authenticate callers.
6. Define reusable guards for API, Streamlit, internal services, and future command handlers.
7. Preserve current local development preview behavior through explicit non-production modes.
8. Prepare for future Supabase/PostgreSQL adapters without embedding either in core contracts.
9. Preserve current API payload meanings and read-only surface during v0.15.
10. Make actor and tenant attribution deterministic, bounded, privacy-safe, and auditable.

## 3. Non-Goals

- Implementing authentication, authorization, tenant fields, migrations, or runtime wiring in this planning phase.
- Public mutation endpoints, upload actions, or Streamlit write controls.
- Supabase, PostgreSQL, OAuth/OIDC, SAML, or external identity-provider integration.
- Password storage, account registration, invitations, password reset, or session UI.
- Tenant billing, subscription policy, or tenant provisioning workflows.
- ERP/export execution permissions beyond reserved permission names and future guard points.
- Fine-grained field redaction, attribute-based policy DSL, or document-sharing links.
- Authentication for legacy competitor-price modules, `dashboard.py`, or legacy `src/api/app.py`.

## 4. Current State

- Document Intelligence API middleware sanitizes request IDs and applies safe headers, but resolves no identity.
- API routes are GET-only and delegate to providers without authorization guards.
- Streamlit supports `local_preview` and unauthenticated `api_preview`; workspace selection is display-only.
- Document State records lack `tenant_id`, ownership, and creator/updater attribution.
- Query Facade filters by document/review/workflow status but not tenant.
- Writers receive repository ports and commands; they do not authenticate users.
- Correction and audit records include `actor_id`, but it is not tied to a verified principal or tenant.
- SQLite is local/dev durability; no production tenant schema or row-level security exists.

## 5. Architecture Decision

Create a provider-neutral security boundary under proposed package `src/security/`.

```text
Request or internal call
  -> IdentityProvider resolves Principal
  -> AuthorizationContextFactory selects active tenant and request context
  -> PermissionGuard evaluates policy
  -> AuthorizationDecision (allow or deny with stable code)
  -> authorized read scope or writer attribution
  -> existing Query Facade / writer / repository boundary
```

Authentication answers who the actor is. Authorization answers whether that actor may perform one permission against one tenant-scoped resource. Tenant filtering is derived from an allowed decision, never trusted directly from a request query parameter.

## 6. Proposed Package And Module Boundaries

```text
src/security/
  __init__.py
  contracts.py
  principals.py
  permissions.py
  roles.py
  policies.py
  decisions.py
  errors.py
  context.py
  guards.py
  providers/
    __init__.py
    local.py
    future_supabase.py  # documentation placeholder only until approved

tests/security/
```

- `contracts.py`: tenant, resource scope, actor attribution, and shared immutable primitives.
- `principals.py`: user, service-account, and system principal contracts.
- `permissions.py`: fixed permission catalog; no dynamic executable permissions.
- `roles.py`: deterministic role definitions and role-to-permission resolution.
- `policies.py`: pure default-deny tenant and permission policy evaluation.
- `decisions.py`: allow/deny decisions and stable policy-result codes.
- `errors.py`: privacy-safe authentication/configuration failures.
- `context.py`: request/internal authorization context and active-tenant selection.
- `guards.py`: reusable authorization boundary that returns authorized scopes.
- `providers/local.py`: deterministic fake identities for test/local preview only.
- Future provider adapters map external claims into core `Principal`; core modules never import Supabase.

## 7. Core Contracts

### Principal

Immutable identity with:

- `principal_id`
- `principal_type`: `user`, `service_account`, or `system`
- `display_name` optional and bounded
- tenant memberships and tenant-scoped role bindings
- directly granted scoped permissions only where explicitly approved
- `is_authenticated`
- provider-neutral authentication method/code
- safe metadata limited to bounded scalar claims

Tokens, credentials, raw provider claims, email addresses, and secrets are not propagated into business records or logs by default.

### Tenant

Immutable tenant identity with `tenant_id`, bounded name/code, lifecycle status, and optional workspace policy. Tenant provisioning and persistence are deferred.

### Role And Permission

Roles are named bundles; permissions are stable action identifiers. Policy resolves both into an immutable effective set. Unknown roles/permissions fail closed.

### ResourceScope

Describes the resource being accessed without carrying payload data:

- required `tenant_id` in authenticated mode
- optional `workspace_id`
- resource type and optional opaque resource ID
- optional bounded access tags
- explicit cross-tenant intent flag only for supported administrative operations

### AuthorizationContext

Contains the verified principal, active tenant, request/correlation ID, execution mode, and safe actor attribution. It is created by trusted composition, not by route payloads or writer metadata.

### AuthorizationDecision And PolicyResult

Immutable allow/deny output containing:

- `allowed`
- requested permission
- normalized authorized scope
- stable reason code such as `allowed`, `missing_identity`, `permission_denied`, `tenant_denied`, `cross_tenant_not_enabled`, or `invalid_scope`
- safe policy/version identifier
- optional audit requirement flag

Decisions contain no raw token, provider exception, repository detail, or resource payload.

## 8. Permission Catalog

Initial permission names to reserve and validate:

- `document:read`
- `document:list`
- `document:ingest`
- `document:review`
- `document:approve`
- `document:export`
- `document:admin`
- `workflow:read`
- `workflow:run`
- `audit:read`
- `tenant:admin`
- `user:admin`

Permissions do not create endpoints or operations. Mutation permissions are placeholders for future command boundaries.

## 9. Role Model

Recommended baseline mappings:

| Role | Baseline permissions |
| --- | --- |
| `platform_admin` | All fixed v1 permissions; cross-tenant access still requires explicit enablement and audited scope |
| `tenant_admin` | Operations-manager permissions plus `document:ingest`, `document:export`, `audit:read`, `tenant:admin`, and `user:admin` within the active tenant |
| `operations_manager` | Reviewer permissions plus `document:approve` and `workflow:run` |
| `reviewer` | Viewer permissions plus `document:review` |
| `viewer` | `document:list`, `document:read`, and `workflow:read` |
| `service_account` | No baseline permission grant; every permission and tenant scope is explicitly assigned for the service purpose |

Role mappings must be fixed and tested in v1. Direct grants are exceptional, bounded, and tenant-scoped. Deny wins over allow if a future explicit-deny mechanism is introduced.

## 10. Tenant Isolation Rules

1. Authenticated operations require an active tenant scope unless explicitly platform-global.
2. A principal may access only tenants present in verified membership or service-account scope.
3. Tenant IDs supplied by clients are selection requests, not authorization proof.
4. `platform_admin` cross-tenant access requires the role, the requested permission, explicit cross-tenant enablement in context, and audit attribution.
5. Service accounts require explicit tenant IDs and permission scopes; no wildcard by default.
6. Resource-by-ID reads must verify tenant ownership. Cross-tenant misses return a privacy-safe not-found result to reduce identifier disclosure.
7. List queries always receive an authorized tenant filter from the guard/composition layer.
8. Audit reads require `audit:read` and tenant scope; platform-wide audit is separately enabled and audited.
9. Workspace and access-tag narrowing may restrict an allowed tenant but cannot broaden it.
10. Missing identity or missing tenant scope denies in authenticated/production modes.

## 11. Document Ownership And Visibility

Recommended future fields:

- `tenant_id`: required on all tenant-owned operational records.
- `workspace_id`: optional secondary partition within a tenant.
- `created_by`: verified principal ID that created the record.
- `updated_by`: verified principal ID for mutable projection updates.
- `owner_principal_id`: optional business owner, not an authorization shortcut.
- `source_system`: optional bounded source code.
- `access_tags`: optional bounded immutable tags for later policy narrowing.

All child records should carry `tenant_id` directly, even when linked to a document, so repository queries and future database constraints cannot accidentally join across tenants. Public read models need not expose these fields merely because persistence gains them.

Visibility is tenant-first. Owner and access tags may narrow visibility later; they never permit cross-tenant access.

## 12. Document State Boundary

Document State validates and stores tenant/ownership fields but does not evaluate permissions or authenticate callers. Future repository ports must support tenant-scoped get/list/write operations and reject missing tenant scope in secured composition.

Migration should add explicit relational columns, indexes, and foreign-key/check constraints where supported. Tenant identity must not be hidden in metadata or opaque JSON. Existing safe metadata rules remain in force.

## 13. Query Facade Filtering Strategy

Query Facade remains read-focused. It accepts normalized tenant read scope and applies it to every supported read:

- document list/detail
- processing, validation, and matching reads
- review cases and correction history
- reprocess plans
- workflow runs
- audit events

Authenticated composition should expose a tenant-scoped facade wrapper/port that cannot be called without an `AuthorizedReadScope`. The security guard creates that scope; request query parameters cannot. Existing unscoped facade remains available only to explicit local preview/test composition during migration.

The Query Facade does not decide roles or permissions. It must enforce the already-authorized tenant filter consistently and fail closed if secured mode receives no scope.

## 14. API Authorization Guard Strategy

Future request flow:

```text
Request
  -> IdentityProvider resolves Principal
  -> AuthorizationContext is built
  -> PermissionGuard evaluates policy
  -> provider receives authorized query scope
  -> response remains privacy-safe
```

- Authentication belongs in middleware/dependencies or an application-level context factory.
- Permission guards are reusable route dependencies/application services, not inline `if role` blocks.
- Routes declare required permissions but do not implement policy.
- Provider/facade calls receive only scopes produced by successful guards.
- Missing/invalid credentials map to safe `401`; authenticated denial maps to safe `403`; cross-tenant resource IDs should normally map to `404`.
- Existing request IDs, envelopes, error sanitation, headers, and GET-only methods remain unchanged.
- No mutation endpoints are introduced in v0.15.

## 15. Streamlit Authorization Strategy

Streamlit remains a consumer of the Document Intelligence API and does not evaluate authoritative permissions locally.

- `local_preview`: deterministic fake local principal and tenant in explicitly non-production mode.
- `api_preview`: preserve current unauthenticated local behavior during migration; optionally accept a future development credential without storing it in fixtures or logs.
- future production mode: requires API-authenticated identity; no local fallback, no direct repository reads, and no client-side role-only enforcement.

UI may hide unavailable controls for usability, but backend guards remain authoritative. Once auth mode is enabled, Streamlit must not bypass the API or select arbitrary tenant scope.

## 16. Writer Authorization And Attribution

Writers do not authenticate principals and do not resolve roles. A future security-aware command gateway performs authorization before constructing writer commands.

```text
Verified AuthorizationContext
  -> command PermissionGuard
  -> authorized writer scope + ActorAttribution
  -> existing writer service
  -> tenant-aware Document State write ports
```

Writer contracts should later carry trusted `tenant_id` and actor attribution supplied by the gateway/composition layer. Writers validate consistency between command scope, related records, and repositories; they do not reinterpret identity-provider claims. Internal service and system actors use explicit principal types and scoped permissions.

## 17. Audit Attribution

Future audit records should include explicit relational fields for:

- `tenant_id`
- optional `workspace_id`
- `actor_principal_id`
- `actor_type`
- authentication/provider method code where safe
- requested permission and decision/reason code for security-sensitive actions
- request/correlation ID
- optional impersonation/delegation reference if ever approved

Never persist tokens, credentials, raw claims, authorization headers, or raw policy exceptions. Cross-tenant platform-admin actions and denied high-risk actions should be auditable without leaking resource data.

## 18. Local, Development, And Test Identity

- Provide a deterministic `LocalIdentityProvider` only in explicit local/test configuration.
- Fixtures include fixed tenant, user, service-account, and system principals.
- Local provider is never selected implicitly and cannot be activated in production mode.
- Production composition fails closed when no real identity provider is configured.
- Tests may inject principals directly through public security contracts without network or token parsing.
- Current `local_preview` and local `api_preview` remain available until production composition is approved.

## 19. Supabase And PostgreSQL Compatibility

Core security contracts remain provider-neutral. A future Supabase adapter may validate/map external JWT claims and memberships into `Principal`; it must not leak Supabase claim shapes into policies, records, writers, or Query Facade contracts.

Future PostgreSQL/Supabase persistence should use tenant columns and indexes. Row-level security is recommended as defense in depth, not a replacement for application guards and tenant-scoped repository contracts. Service-role credentials must never be available to UI clients.

## 20. Migration Strategy

1. Introduce security contracts, policy catalog, guards, and deterministic local provider without changing current runtime composition.
2. Add tenant/actor fields to contracts and repository interfaces behind a versioned compatibility layer.
3. Add nullable/backfillable relational columns in a future migration, assign existing local data to an explicit deterministic legacy/local tenant, then enforce non-null tenant constraints for secured records.
4. Add tenant-aware repository indexes and uniqueness/idempotency scopes such as `(tenant_id, stable_id)`.
5. Add tenant-scoped Query Facade adapter and compare results against existing local preview.
6. Add API security composition in opt-in development mode; production mode remains disabled until a real provider is configured.
7. Add Streamlit authenticated API mode without removing local preview.
8. After compatibility verification, prohibit unscoped repository/facade paths in production composition.

No migration file or schema change is part of this planning task.

## 21. Testing Strategy

- Principal, tenant, role, permission, context, decision, and serialization validation.
- Fixed role-to-permission matrix and unknown-value rejection.
- Default-deny allow/deny decisions.
- Tenant membership and active-tenant enforcement.
- Explicit audited platform-admin cross-tenant access.
- Service-account tenant and permission scope enforcement.
- Missing identity and missing/unsafe tenant filter denial.
- API guard behavior with safe `401`, `403`, and tenant-hiding `404` outcomes.
- Query Facade tenant filtering for every read family, get-by-ID, pagination, and counts.
- Writer gateway authorization and trusted tenant/actor attribution.
- Audit actor/tenant attribution and metadata privacy.
- Local provider determinism and production-mode rejection.
- Backward-compatible local preview and existing API payload tests.
- Recursive forbidden-import and no-bypass boundary tests.

## 22. Security And Privacy Requirements

- Default deny in authenticated modes.
- Constant/bounded error templates; no raw token, provider, SQL, stack, or policy detail.
- Credentials and raw claims never enter metadata, read models, audit payloads, logs, or exceptions.
- Tenant selection is validated against verified memberships.
- Cross-tenant administration requires explicit intent and audit.
- Service accounts are least-privilege and non-interactive.
- System actors are explicit and cannot be supplied by clients.
- Security decisions are deterministic, immutable, and testable.
- Authorization context is request/task scoped and must not leak between concurrent operations.

## 23. Proposed Implementation Phases

1. **Security contracts and role catalog:** core contracts, permissions, roles, decisions, errors, local identities, ADR alignment, and boundary tests.
2. **Policy engine and guards:** pure policies, context construction, default-deny guards, tenant/cross-tenant/service-account tests.
3. **Tenant-aware Document State and Query Facade contracts:** versioned tenant/ownership fields, repository/query scopes, compatibility mapping, schema/migration design and conformance tests.
4. **Read-only API security integration:** opt-in API guards, authorized provider scope, local compatibility mode, and safe unauthorized responses; no public mutations.
5. **Streamlit auth-mode preview:** optional allowlisted local-demo identity headers in `api_preview`, fixed safe unauthorized states, and unchanged default `local_preview`; the API remains authoritative.
6. **Verification, documentation, and release closure:** boundary/privacy verification, full regression, summary, handoff, release notes, and migration/production-readiness decision.

Phase 1 delivered the standard-library-only `src/security/` contracts, exact permission and role catalogs, explicit anonymous/user/service/system principals, immutable authorization context and decisions, privacy-safe errors, and a pure default-deny policy evaluator. Identity-provider adapters, reusable guards, and all API, UI, storage, Query Facade, and writer integration remain deferred to later phases.

Phase 2 delivered a provider-neutral identity resolution Protocol and safe result contract, an explicit local/dev/test provider with deterministic demo identities, a bounded authorization request contract, and a pure permission guard that delegates to the Phase 1 policy evaluator. API, Streamlit, Document State, Query Facade, writer, persistence, and external identity-provider integration remain deferred.

Phase 3 delivered the first tenant-aware operational projection: `DocumentRecord` now carries explicit tenant, workspace, actor, owner, source-system, and access-tag fields; document repositories and the Workflow Query Facade accept optional tenant narrowing; and SQLite migration `002` persists and indexes those fields. Existing constructors use deterministic `tenant-local` compatibility, and API payloads intentionally omit internal tenant fields. Tenant columns for child records and authenticated enforcement remain later work.

Phase 4 delivered opt-in authorization for the existing Document Intelligence API GET surface. The app factory owns explicit disabled/local-demo/authenticated/production modes, resolves identity through the provider Protocol, delegates all role decisions to `PermissionGuard`, and passes one narrowed tenant scope into provider reads. Default local preview remains unauthenticated; no Streamlit, writer, mutation, database, or external-provider integration was added.

Phase 5 delivered a development-only Streamlit auth preview for `api_preview`. The GET-only API client can send one fixed local-demo identity header selected from an allowlist, while `local_preview` remains the default and sends no auth context. Streamlit does not evaluate permissions, select cross-tenant scope, store credentials, or reflect backend exception details; API authorization remains authoritative. Writer enforcement, production identity, and release closure remain deferred.

Phase 6 completed focused and full regression verification, confirmed boundary compliance and API/UI compatibility, and added the v0.15 summary, handoff, release notes, roadmap, debt, ADR, plan, and changelog closure. Production composition, real identity providers, writer enforcement, and child-record tenant expansion remain deferred.

## 24. Risks And Mitigations

- **Tenant data leakage:** mandatory normalized tenant scope, get-by-ID ownership checks, and end-to-end negative tests.
- **Inline policy drift:** centralized permission guard and declarative route permission requirements.
- **Role explosion:** small fixed baseline roles; policies evaluate permissions, not role names.
- **Platform-admin overreach:** explicit cross-tenant enablement and mandatory audit.
- **Service-account wildcard access:** no implicit wildcard; explicit tenant and permission scope.
- **Local-mode production bypass:** explicit mode selection and production fail-closed validation.
- **Breaking existing data:** staged backfill to a named local tenant and versioned compatibility contracts.
- **Repository/business coupling:** repositories store/filter tenant data but do not decide authorization.
- **Provider lock-in:** adapters map external identity into provider-neutral contracts.
- **UI-only enforcement:** API guard remains authoritative; Streamlit visibility is advisory.

## 25. Acceptance Criteria

- Architecture clearly separates authentication, authorization, tenant filtering, storage, reads, and writes.
- Core concepts and fixed role/permission catalogs are specified.
- Tenant isolation is mandatory and testable in authenticated composition.
- API and Streamlit guard flows preserve existing read-only contracts.
- Document State and Query Facade impacts have a versioned migration path.
- Writers remain authentication-free and receive trusted attribution only after authorization.
- Local preview compatibility and production fail-closed behavior are explicit.
- Supabase/PostgreSQL remain future adapters, not core dependencies.
- Implementation is split into narrow phases with tests and stop conditions.
- No code, tests, dependencies, endpoints, UI, or migrations are changed during planning.

## 26. Deferred Work

- Real identity-provider adapter and token verification.
- Supabase Auth, PostgreSQL repositories, RLS policies, and production provisioning.
- User/tenant administration APIs and UI.
- Public mutation endpoints, uploads, workflow commands, and review commands.
- Invitations, sessions, refresh/revocation, MFA, SSO, and account recovery.
- Tenant billing, quotas, legal hold, retention, and data residency.
- ERP/export execution and elevated recovery command implementation.
- Field-level redaction, sharing, delegated access, and impersonation.
- FlowSync Document Intelligence authentication.
- OCR, LLM, and external services.
