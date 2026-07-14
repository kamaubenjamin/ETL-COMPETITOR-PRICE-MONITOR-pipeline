# ADR-022: FlowSync Document Intelligence UI Boundary

## Status

Accepted for v0.17. Phase 1 implements the approved frontend boundary; later product views remain pending.

## Context

The platform now provides a separate versioned Document Intelligence API, Workflow Query Facade, durable Document State, lifecycle/writer integration, tenant-aware authorization, explicit runtime composition, and an internal Streamlit operator console. A production-style product UI is the next milestone.

The repository also contains a legacy Competitor Price dashboard and API concerns. Reusing that product surface for Document Intelligence would couple unrelated routes, stores, telemetry, mutations, and security assumptions. Streamlit is an internal console and likewise must not become the product frontend architecture.

An approved v0.17 mockup establishes a clean enterprise direction with sidebar navigation, a tenant/user-aware header, document dashboard, document detail, validation, matching, review/correction, lifecycle/workflow history, audit, and explicit unauthorized/unavailable states. It does not create backend capabilities or require pixel-perfect implementation.

## Decision

Create FlowSync Document Intelligence as an independent, read-first HTTP client of the versioned Document Intelligence API.

The UI will:

1. use an isolated application or feature package in the owner-confirmed FlowSync host
2. consume only public versioned API contracts
3. keep API transport, view-model shaping, pages, and presentation components separate
4. preserve API ownership of authentication, authorization, tenant scope, resource visibility, and errors
5. implement document, validation, matching, review, workflow, and audit views as read-only in v0.17
6. represent unsupported previews and actions as explicit unavailable/future states
7. use the approved mockup as an information-architecture and visual-direction reference
8. remain themeable and responsive without changing backend contracts

The owner-approved application location is `apps/flowsync-document-intelligence/`. Phase 1 creates an isolated Vite, React, and TypeScript package there with no imports from backend Python packages, Streamlit, or competitor-price modules. Dependency installation is explicit and remains outside repository automation.

## Product Separation Decision

FlowSync Document Intelligence does not import, route through, or share domain state with:

- FlowSync Competitor Price
- root `dashboard.py`
- legacy `src/api/app.py`
- Streamlit components/providers
- backend repositories or runtime implementations

Generic design-system components and neutral session/HTTP infrastructure may be reused only after confirming they carry no competitor-price business behavior.

## API Boundary Decision

The API client validates `success`, `data`, `error`, `metadata`, `api_version`, and `request_id` envelopes and supports only allowlisted GET routes, filters, and bounded pagination in v0.17.

The client never imports Python backend contracts as executable dependencies, selects a persistence backend, constructs runtime services, or silently falls back to fixtures. Unsupported or unavailable API composition becomes a visible safe UI state.

## Route Decision

Initial product routes are:

- `/documents`
- `/documents/:documentId`
- `/documents/:documentId/validation`
- `/documents/:documentId/matching`
- `/review`
- `/review/:reviewCaseId`
- `/workflows`
- `/audit`
- optional `/settings/runtime-preview`
- `/unauthorized`
- `/unavailable`

The route set is a client information model, not authorization policy. API responses remain authoritative.

## Auth And Tenant Decision

The UI may consume an approved outer session adapter later but does not parse provider claims or decide permissions. Tenant scope is established by authenticated API context. Client filters and route parameters cannot broaden it.

Raw tenant IDs, claims, tokens, credentials, and provider details are not rendered. Safe user/workspace labels require an approved public/session contract. Concealed API `404` responses remain concealed.

## Read-First Decision

No upload, correction, review decision, assignment, reprocess request, workflow execution, or export action is enabled until versioned command contracts, authorization, idempotency, concurrency, audit, and error behavior are separately approved.

The current API exposes neither raw document preview nor raw correction values. UI regions from the mockup that imply those capabilities display safe placeholders or summaries in v0.17.

## Visual Decision

The mockup guides hierarchy and interaction direction: enterprise sidebar, top context header, operational status cards, filterable tables, detail tabs, field-level quality views, confidence-oriented matching, review comparison layout, timelines, audit tables, and explicit error cards.

Final colors, typography, animation, exact spacing, and pixel parity are not architectural requirements. The implementation should use semantic design tokens and existing owner-approved FlowSync primitives so theming can evolve independently.

## Privacy And Safety Decision

The UI, logs, URLs, analytics, browser storage, and error states exclude raw documents/rows, correction values, artifact payloads, storage paths, tenant IDs, credentials, tokens, claims, environment values, provider references, stack traces, raw exceptions, and unrestricted audit metadata.

## Runtime Composition Decision

FlowSync consumes a separately deployed Document Intelligence API. It does not import `platform_runtime` or activate `RuntimeConfig`. v0.16 production fail-closed behavior remains binding; UI availability cannot make an unsupported backend/auth combination valid.

## Consequences

### Positive

- Product and legacy competitor-price concerns stay isolated.
- One HTTP contract supports FlowSync and the internal Streamlit consumer without sharing UI code.
- Tenant and permission enforcement remains centralized.
- Unsupported mutations and sensitive values cannot be accidentally implied as implemented.
- The approved mockup can guide a coherent product without freezing the design system.

### Negative

- The frontend host/toolchain must be confirmed before implementation.
- Several mockup regions remain placeholders because safe read/mutation contracts do not exist.
- Real production auth and runtime adapters remain prerequisites for production deployment.
- Some lifecycle correlations may require a future additive API contract.

## Alternatives Rejected

### Extend the competitor-price dashboard

Rejected because it mixes products, routes, state, telemetry, mutations, and security boundaries.

### Reuse Streamlit as the product frontend

Rejected because Streamlit is an internal operator console with separate provider and deployment assumptions.

### Let FlowSync import repositories or Query Facade

Rejected because it bypasses API authorization, envelopes, runtime composition, and tenant-safe read boundaries.

### Implement mockup actions locally

Rejected because client-only corrections, review decisions, uploads, or exports would create false state and bypass backend audit/concurrency rules.

### Select a new frontend framework during planning

Rejected because the owner-confirmed FlowSync host and toolchain are not present in the targeted repository context.

## Deferred Decisions

- FlowSync host repository and exact framework/package layout.
- Real identity/session provider and token handling.
- Upload, correction, decision, assignment, reprocess, workflow, and export command contracts.
- Protected raw document preview and corrected-value access.
- Additive lifecycle/detail APIs if current records cannot support the intended timeline.
- Production deployment, CSP, telemetry, analytics, localization, and final visual theme.

## Acceptance

ADR-022 is accepted when owners approve the independent product boundary, API-only read model, route/page architecture, API-authoritative auth/tenant behavior, mockup-as-direction posture, privacy rules, six-phase implementation sequence, and requirement to confirm the FlowSync host before source creation.
