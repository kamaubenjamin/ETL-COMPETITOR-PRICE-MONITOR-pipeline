# ADR-020: Auth, Tenant, And Permission Boundaries

## Status

Accepted for v0.15. Phase 1 contracts, catalogs, context, decisions, privacy-safe errors, and pure default-deny policy evaluation are implemented; provider adapters, guards, and runtime integration remain pending.

## Context

The Document Intelligence Platform has durable operational state, a read-only Workflow Query Facade, a versioned GET-only API, and local/API Streamlit preview modes. It does not yet authenticate callers, isolate tenants, resolve roles/permissions, or bind actor identifiers to verified principals.

Adding security directly to routes, UI components, repositories, Query Facade methods, or writers would duplicate policy and create bypass paths. Hard-coding Supabase claims would also couple core contracts to one provider before production identity and database decisions are approved.

## Decision

Create a provider-neutral security boundary under proposed package `src/security/`.

The boundary separates:

1. **Authentication:** an `IdentityProvider` maps credentials or trusted local context to an immutable `Principal`.
2. **Context construction:** trusted composition selects the active tenant and creates `AuthorizationContext`.
3. **Authorization:** a default-deny `PermissionGuard` evaluates a stable permission against a tenant-aware `ResourceScope`.
4. **Enforcement:** successful decisions produce normalized authorized scopes consumed by read providers or future command gateways.
5. **Attribution:** trusted actor/tenant attribution is propagated to writers and audit records without raw credentials or claims.

Core security contracts and policy do not depend on FastAPI, Streamlit, Document State, Query Facade, writers, Supabase, PostgreSQL, or external services.

## Package Decision

Use `src/security/` rather than placing policy under API, Document State, Workflow Runtime, or UI.

- API is one consumer and must not own platform policy.
- Document State remains storage-focused.
- Query Facade remains read-focused.
- Writers remain operation-focused and do not authenticate users.
- Streamlit remains a consumer and cannot be authoritative.

Provider adapters live below `src/security/providers/` and map inward to stable contracts. `future_supabase.py` is a planning placeholder only; it must not be created as executable integration until separately approved.

## Identity Decision

`Principal` supports three explicit types:

- `user`: interactive authenticated person.
- `service_account`: non-interactive identity with explicit tenant and permission scopes.
- `system`: trusted internal actor created only by approved composition.

Principal contracts contain opaque IDs, tenant memberships, role bindings, scoped grants, authentication method code, and bounded safe metadata. They exclude tokens, credentials, raw provider claims, and secrets.

Local/test composition may use deterministic fake principals. Production composition must reject local identity providers and fail closed when real authentication is unavailable.

## Role And Permission Decision

Authorization policy evaluates permissions, not role names. Roles are deterministic bundles that resolve to stable permission values.

Initial roles:

- `platform_admin`
- `tenant_admin`
- `operations_manager`
- `reviewer`
- `viewer`
- `service_account`

Initial permission catalog:

- document list/read/ingest/review/approve/export/admin
- workflow read/run
- audit read
- tenant admin
- user admin

Unknown values reject. Service accounts receive no broad implicit wildcard. Platform-admin cross-tenant access requires explicit context enablement and audit.

## Tenant Isolation Decision

Authenticated operations require an authorized active tenant unless explicitly platform-global. A tenant ID supplied by a request is only a requested selection; the guard intersects it with verified memberships/scopes.

Resource-by-ID reads verify tenant ownership. Tenant mismatches normally return not-found to avoid identifier disclosure. List/count/pagination reads receive guard-produced tenant scope. Workspace and access tags may narrow a tenant scope but never broaden it.

Every tenant-owned Document State record should eventually carry explicit `tenant_id`; linked child records should not rely solely on document joins. Tenant fields are relational contract/schema fields, not metadata.

## Read Boundary Decision

The Query Facade does not authorize. In authenticated composition it accepts a normalized tenant read scope and applies it consistently to documents, processing, validation, matching, review, correction, reprocess, workflow, and audit reads.

The API resolves identity and invokes reusable guards outside route business logic. Routes declare required permissions, then providers receive only authorized scope. Existing paths, GET-only methods, payload meanings, envelopes, request IDs, and security headers remain stable.

Streamlit uses the API in authenticated modes. It may hide controls for usability but cannot grant access or bypass server guards.

## Write Boundary Decision

Writers do not authenticate or resolve roles. A future command gateway receives verified authorization context, checks the relevant permission, creates trusted tenant/actor attribution, and then invokes existing writers with tenant-aware write ports.

No public mutation endpoint is added by v0.15 planning. Reserved mutation permissions describe future guard requirements only.

## Audit Decision

Security-sensitive audit records should include tenant, optional workspace, verified actor ID/type, request/correlation ID, requested permission, and bounded policy result code. Cross-tenant administrative actions require audit.

Tokens, credentials, raw claims, authorization headers, raw policy exceptions, and resource payloads are never persisted in audit metadata.

## Compatibility Decision

- Preserve explicit `local_preview` with deterministic fake identities for development/test.
- Preserve current local `api_preview` during migration.
- Production/authenticated mode has no unauthenticated or local fallback.
- Existing API payloads do not expose tenant fields merely because persistence gains them.
- Existing unscoped repository/facade paths may remain behind explicit local compatibility composition until migration is complete; they are forbidden in production composition.

## Supabase/PostgreSQL Decision

Supabase may later provide an identity adapter and managed PostgreSQL, but it is not the core security model. External claims map to `Principal`. PostgreSQL row-level security is defense in depth and does not replace application guards, tenant-scoped ports, or tests.

## Alternatives Rejected

- **Inline route role checks:** duplicates policy and makes consistency/testing difficult.
- **UI-only authorization:** bypassable and unsuitable as a source of truth.
- **Repository-owned roles:** mixes storage with business/security policy.
- **Writer authentication:** couples internal deterministic writers to transport/provider concerns.
- **Caller-supplied tenant filters:** permits accidental or malicious scope broadening.
- **Supabase-specific core claims:** creates provider lock-in and leaks external schema across boundaries.
- **Platform-admin implicit global access:** too broad and insufficiently auditable.

## Consequences

### Positive

- One default-deny policy boundary serves API, UI consumers, internal services, and future commands.
- Tenant isolation becomes explicit, testable, and provider-neutral.
- Storage, read, and write layers retain focused responsibilities.
- Local development remains deterministic while production fails closed.
- Future Supabase/PostgreSQL adoption remains an adapter/composition choice.

### Negative

- Document State and Query Facade contracts require a staged tenant-aware migration.
- Compatibility modes temporarily create both scoped and explicitly local unscoped paths.
- Every read family and future command needs guard and tenant-isolation tests.
- Event/audit attribution fields require future schema work and backfill decisions.

## Security Risks

- Tenant scope omission or confused-deputy behavior.
- Platform-admin or service-account overreach.
- Local identity provider accidentally enabled in production.
- Route/provider bypass of guards.
- Cross-tenant ID existence disclosure.
- Tokens or claims leaking into metadata/audit/errors.
- Migration records assigned to the wrong tenant.

Mitigations are default deny, explicit modes, guard-produced scope, mandatory negative tests, stable privacy-safe errors, cross-tenant audit, versioned migrations, and no silent fallback.

## Deferred Decisions

- Real identity provider, token verification, sessions, refresh/revocation, MFA, and SSO.
- Supabase Auth/PostgreSQL implementation and row-level security policies.
- User/tenant administration endpoints and UI.
- Public mutations, upload API/UI, workflow/review commands, and ERP/export execution.
- Field-level redaction, delegated sharing, impersonation, and legal/retention policy.
- FlowSync Document Intelligence authentication.
- OCR, LLM, and external services.

## Compatibility

ADR-020 is additive to ADR-014 through ADR-019. It preserves current read-only API/UI behavior during migration and does not modify legacy `src/api/app.py`, root `dashboard.py`, or competitor-price modules.
