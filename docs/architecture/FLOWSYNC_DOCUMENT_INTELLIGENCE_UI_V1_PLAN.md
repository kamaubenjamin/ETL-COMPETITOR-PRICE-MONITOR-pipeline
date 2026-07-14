# FlowSync Document Intelligence UI v1 Plan

**Milestone:** v0.17
**Status:** Phase 1 implemented; Phase 2 not started
**Product surface:** FlowSync Document Intelligence

## 1. Problem Statement

The platform has a versioned read-only Document Intelligence API, governed runtime composition, tenant-aware authorization boundaries, and an internal Streamlit operator console. It does not yet have a production-style product UI for document operations. The existing FlowSync Competitor Price experience and root `dashboard.py` belong to a separate legacy product and cannot be extended into the Document Intelligence UI without mixing routes, state, ownership, and security assumptions.

v0.17 defines a separate FlowSync Document Intelligence application that consumes the Document Intelligence API over HTTP. The approved v0.17 visual mockup establishes the product direction: an enterprise shell, document dashboard, detail and quality views, review context, workflow history, audit visibility, and explicit unauthorized/unavailable states. The mockup is directional rather than a pixel-perfect implementation contract.

## 2. Goals

1. Establish an independent FlowSync Document Intelligence product boundary.
2. Define an app shell, route model, API client boundary, and read-first page architecture.
3. Present document lifecycle, validation, matching, review, workflow, and audit data from existing API contracts.
4. Keep the API authoritative for identity, tenant scope, permissions, visibility, and errors.
5. Define safe loading, empty, unauthorized, forbidden, concealed-not-found, unavailable, and malformed-response states.
6. Preserve v0.9+ API paths and v0.16 runtime composition boundaries.
7. Make the UI themeable and responsive without coupling backend contracts to presentation.
8. Create a phased path for later upload, correction, review decisions, reprocessing, and export after approved mutation contracts exist.

## 3. Non-Goals

- Implementing UI source, modifying FlowSync, or selecting/installing a frontend dependency during planning.
- Pixel-perfect reproduction of the approved mockup.
- Changing Streamlit or sharing Streamlit components, providers, or state.
- Adding API endpoints, mutation routes, database migrations, or runtime behavior.
- Implementing authentication, token issuance, tenant selection, or permission policy.
- Uploading documents, submitting corrections/decisions, requesting reprocessing, running workflows, or exporting to ERP.
- Displaying raw documents, raw rows, raw correction values, credentials, claims, stack traces, or backend internals.
- Modifying root `dashboard.py`, legacy `src/api/app.py`, or competitor-price modules.

## 4. Current State

- The separate Document Intelligence API exposes versioned GET-only health, status, documents, processing, validation, matching, review, correction-history, reprocess-plan, workflow-run, and audit endpoints.
- API envelopes contain `success`, `data`, `error`, `metadata`, `api_version`, and `request_id`.
- v0.15 provides API-authoritative permission checks and tenant-narrowed reads for supported configurations.
- v0.16 provides explicit runtime composition and deliberately fails closed for unsupported production configurations.
- Streamlit is an internal read-only console with `local_preview` and `api_preview`; it is not the FlowSync product architecture.
- Phase 1 establishes the owner-approved isolated Vite, React, and TypeScript application at `apps/flowsync-document-intelligence/`. It includes the app shell, route metadata, static safe pages, GET-only API contracts, strict envelope parsing, fixed safe errors, and semantic theme foundations. Dependencies are declared but not installed by repository automation.

## 5. UI Product Boundary

FlowSync Document Intelligence is an independent API client. Its source, routes, deployment configuration, session integration, tests, and design tokens must remain separate from:

- FlowSync Competitor Price and its execution/telemetry concerns
- root `dashboard.py`
- legacy `src/api/app.py`
- the internal Streamlit console
- backend repositories, Document State, Query Facade implementations, writers, security policy, and `platform_runtime`

The product may share an owner-approved FlowSync design system and generic HTTP/session primitives if they are dependency-neutral. It must not share competitor-price domain components, stores, routes, fixtures, or business rules.

## 6. Recommended UI Architecture

Use a layered frontend boundary:

```text
FlowSync app shell and router
  -> page controllers / query hooks
  -> Document Intelligence view models
  -> Document Intelligence API client
  -> versioned HTTP API
  -> API authorization and app-scoped provider
  -> platform runtime composition
```

The approved frontend location is `apps/flowsync-document-intelligence/`, with these logical modules:

- `app/`: product shell, route registration, top-level providers, and error boundary.
- `api/`: GET-only client, envelope validation, pagination/filter serialization, and safe error mapping.
- `features/documents/`: list, detail, processing, validation, and matching pages.
- `features/review/`: queue, case detail, corrections summary, and reprocess-plan display.
- `features/workflows/`: workflow-run list/detail summaries and lifecycle timeline projection.
- `features/audit/`: bounded audit event list and filters.
- `components/`: product-neutral shell, navigation, status, table, timeline, empty-state, and error-state components.
- `models/`: UI-local typed response and view-model contracts derived from public API payloads.
- `test/`: fixtures, API-client tests, component tests, route tests, and accessibility checks.

The package is a standalone Vite, React, and TypeScript application. It imports no backend Python package, Streamlit module, or competitor-price code. Its dependency installation and build outputs remain local to the application boundary.

## 7. Route And Page Model

| Route | Purpose | Current API source | v0.17 behavior |
| --- | --- | --- | --- |
| `/documents` | Document dashboard and inbox | `GET /api/v1/documents` | Read-only |
| `/documents/:documentId` | Safe document metadata and status | document detail and processing GETs | Read-only |
| `/documents/:documentId/validation` | Field/rule issues | document validation GET | Read-only |
| `/documents/:documentId/matching` | Candidate and confidence results | document matching GET | Read-only |
| `/review` | Review queue | review-case list GET | Read-only |
| `/review/:reviewCaseId` | Case, correction summary, decision/reprocess context | review detail, corrections, reprocess-plan GETs | Read-only |
| `/workflows` | Workflow activity | workflow-run list GET | Read-only |
| `/audit` | Safe audit trail | audit-event list GET | Read-only |
| `/settings/runtime-preview` | Optional safe API/runtime descriptor | status GET | Optional, non-authoritative |
| `/unauthorized` | Authentication/authorization guidance | client state from safe API response | Static safe state |
| `/unavailable` | API/runtime unavailable guidance | client transport/runtime state | Static safe state |

Unknown or unauthorized resource details must follow API semantics. A concealed `404` must not be reinterpreted as proof that a resource exists.

## 8. App Shell And Navigation

The approved direction uses:

- persistent left sidebar on desktop and a compact drawer on smaller screens
- top header with product name plus safe workspace/user context when supplied by an approved session boundary
- primary navigation for Documents, Review, Workflows, and Audit
- contextual document navigation for Overview, Validation, Matching, and History
- consistent breadcrumbs/back navigation for nested document and review pages
- no cross-link into competitor-price routes as if both products share state

Navigation visibility may improve usability but is never permission enforcement. The API must still authorize every request.

## 9. Document List View

The documents dashboard should provide:

- summary counts for received/processing/review-required/failed/export-ready where supplied by data or safely derived from the current result set
- searchable/filterable table using API-supported status and document-type filters
- stable columns for safe document identity, filename, type, status, confidence, current stage, and timestamps when present
- deterministic pagination using API metadata
- clear loading, empty, filtered-empty, unavailable, and unauthorized states
- status labels based on an explicit display catalog, not hidden lifecycle inference

Client-side search must be labeled as current-page filtering unless a server-side search contract exists. The UI must not imply global search coverage unsupported by the API.

## 10. Document Detail And Lifecycle

The detail page should use tabs or subordinate routes for safe metadata, processing/lifecycle, validation, and matching. It may display:

- safe document identity and filename
- document type, current status, current stage, confidence, and timestamps
- deterministic processing steps and workflow/audit entries available through existing GET contracts
- a lifecycle timeline that distinguishes observed API events from UI display labels

The current API does not expose raw document bytes or a sanctioned document-preview contract. The mockup's preview region must therefore render a safe unavailable/placeholder state in v0.17 rather than fetch a storage path or invent raw content access.

## 11. Validation And Matching Views

Validation should show bounded field-level issue summaries: severity, field, rule/code, and safe message. It must not reconstruct or reveal raw field values.

Matching should show candidate identifiers/names, confidence, method/status, and safe explanations supplied by the API. It must not make match decisions locally or infer authoritative thresholds beyond display labels defined by public contracts.

Both views require stable ordering, loading/empty/error states, accessible table semantics, and responsive layouts that preserve comparison readability.

## 12. Review And Correction Views

The review queue should show case identity, reason code, priority, status, assignment summary, correction count, decision summary, and reprocess state when available.

The review detail direction compares extracted and corrected values, but current public projections intentionally exclude raw correction values. v0.17 therefore presents safe correction history summaries and a controlled-value placeholder. Actual before/after values and actions remain blocked until a separately approved protected-value and mutation contract exists.

Approve, reject, correct, skip, request-reprocess, and assignment controls may be represented in planning diagrams only. They must not be enabled or simulated as successful actions.

## 13. Workflow, Lifecycle, And Audit Views

- Workflow pages show run ID, workflow name, status, start time, duration, and safe stage summaries supported by the API.
- Lifecycle presentation combines document processing state and safe correlated events only when identifiers/contracts make the relation explicit.
- Audit pages show timestamp, event type, safe actor label, and allowlisted scalar metadata.
- Raw claims, repository keys, stack traces, payloads, paths, and arbitrary metadata objects are never rendered.

## 14. API Client Boundary

The client must:

- accept an explicit base URL from deployment configuration
- call only the approved versioned GET routes in v0.17
- validate the standard response envelope before exposing data to pages
- serialize only allowlisted filters and bounded pagination parameters
- preserve API ordering and pagination metadata
- map safe API errors to a fixed UI error catalog
- retain a bounded request ID as an optional support reference without exposing internals
- use an injected future session/credential adapter rather than reading or persisting raw credentials in feature code
- never retry unsafe methods; GET retry policy, if added, must be bounded and explicit
- never silently replace unavailable API data with local fixtures in production UI modes

Typed UI contracts mirror public HTTP payloads but do not become backend contracts. Contract drift is detected through fixtures/schema tests and API compatibility tests.

## 15. State, Loading, And Error Model

Each query has explicit states: `idle`, `loading`, `success`, `empty`, `unauthorized`, `forbidden`, `not_found`, `unavailable`, and `invalid_response`.

- `401`: show authentication-required state; do not echo headers or claims.
- `403`: show insufficient-access state; do not suggest a tenant workaround.
- concealed `404`: show generic not-found state.
- safe `400`: show fixed invalid-filter/request guidance.
- `405`: treat as client contract defect; no alternate mutation call.
- safe `500` or transport failure: show unavailable state and optional bounded request reference.
- malformed envelope: fail closed into invalid-response state.

Pages should preserve navigation and safe cached shell state during failures, but must not show stale protected records as current unless a future cache policy explicitly allows and labels that behavior.

## 16. Auth And Tenant-Aware UI Behavior

- Authentication/session integration is an outer FlowSync concern and remains deferred until a real identity adapter exists.
- The UI sends credentials only through the approved client/session adapter.
- Tenant scope comes from authenticated API context; users cannot broaden it with query parameters or local state.
- Tenant IDs and raw claims are not displayed. A safe tenant/workspace display name may appear only when supplied by an approved public/session contract.
- Hidden navigation is convenience only. API `401/403/404` responses remain authoritative.
- Local-demo identity controls are not part of the production product surface.
- Runtime labels are diagnostic display only and cannot activate a mode or backend.

## 17. Privacy And Safety Rules

The UI must not expose or persist:

- raw document contents or rows
- raw correction values
- artifact payloads or storage paths
- tenant IDs or arbitrary access tags
- credentials, tokens, refresh tokens, or raw identity claims
- SQLite paths, DSNs, environment values, or provider references
- stack traces, raw exceptions, or unrestricted audit metadata

Browser logs, analytics, error reporting, URLs, and client storage follow the same rules. Sensitive identifiers must not be placed in query strings beyond the approved opaque route identifiers.

## 18. Design System And Component Strategy

Phase 1 should inventory and reuse an existing FlowSync design system if one is owner-approved. Otherwise define a small semantic-token layer for color roles, spacing, typography, elevation, focus, status, and responsive breakpoints before feature styling.

Core components should include app shell, sidebar, header, breadcrumbs, page header, metric strip, filter toolbar, data table, status/priority label, confidence display, details list, tab navigation, timeline, empty state, error state, skeleton/loading state, and confirmation-disabled placeholder for future actions.

Components own presentation and accessibility, not domain decisions. Status catalogs map exact API values to labels/tokens with a visible unknown fallback. Theme changes must not alter HTTP contracts or view-model semantics.

## 19. Visual Mockup Direction

The approved v0.17 mockup is the product/design reference for:

- clean enterprise dashboard composition
- left sidebar and tenant/user-aware top header
- document status cards and searchable/filterable table
- document detail with preview, metadata, and lifecycle navigation
- field-level validation and confidence-oriented matching views
- review/correction comparison layout
- workflow/lifecycle timeline and audit table
- explicit unauthorized and unavailable cards
- architecture messaging that the UI consumes API-owned state

Implementation should preserve the information hierarchy, calm operational tone, scanability, and secure/read-first language. Exact colors, typography, animation, density tuning, and pixel-level spacing remain later design iterations. Responsive behavior must be designed, not achieved by shrinking desktop typography.

## 20. Runtime Composition Assumptions

FlowSync never imports or constructs `RuntimeConfig`, `RuntimeComposition`, repositories, lifecycle services, writers, Query Facade, or API providers. Deployment points the UI at a separately composed Document Intelligence API. Unsupported pilot/production API compositions remain unavailable, and the UI must show that condition rather than selecting a local backend or falling back to mock data.

## 21. Testing Strategy

- API client envelope, error, pagination, filter, timeout, and GET-only tests.
- Contract fixtures for every consumed v0.9+ response shape.
- Route registration and deep-link tests.
- Page tests for loading, success, empty, filtered-empty, unauthorized, forbidden, concealed-not-found, unavailable, and malformed-response states.
- Component tests for status/priority/unknown values and stable table columns.
- Accessibility tests for keyboard navigation, focus, labels, landmarks, tables, and color-independent status meaning.
- Responsive browser verification at mobile, tablet, and desktop widths.
- Privacy tests for logs, URLs, storage, rendered output, and error states.
- Import/dependency tests proving no backend, Streamlit, or competitor-price coupling.
- API compatibility smoke tests against the existing GET-only application.

## 22. Implementation Phases

1. UI boundary, app shell, route contracts, API client contracts, and framework/host confirmation.
2. Read-only document list and detail views.
3. Read-only validation, matching, review, workflow, and audit views.
4. Auth/tenant-aware display states and unavailable/error hardening.
5. Product polish, accessibility, responsive behavior, tests, and integration verification.
6. Release closure, handoff, and owner tag recommendation.

Each phase is one Codex session and stops before the next phase.

Phase 1 delivers the isolated frontend boundary, responsive enterprise shell, sidebar/header navigation, all approved route contracts, safe static placeholders, status/loading/empty/error components, API-safe TypeScript models, allowlisted endpoint builders, a GET-only client, strict v1 envelope validation, fixed non-reflective errors, semantic design tokens, and explicit package scripts. It makes no live request at startup, installs no dependencies, implements no product data view, auth/session behavior, or mutation, and changes no backend, Streamlit, dashboard, or competitor-price source.

## 23. Deferred Work

- Final frontend host/toolchain selection if FlowSync source remains external.
- Real identity/session provider and production token handling.
- Public upload and document mutation contracts.
- Review correction/decision/assignment and reprocess commands.
- Workflow execution and ERP/export actions.
- Protected raw document preview and encrypted blob access policy.
- Production deployment, CSP, telemetry, analytics, localization, and feature flags.
- Final brand theme, advanced motion, and extended usability research.
- PostgreSQL/Supabase production composition and multi-tenant hardening.

## 24. Risks And Open Questions

- The frontend boundary is now approved and scaffolded in this repository, but dependency installation, lockfile selection, lint/test tooling, and deployment ownership remain to be finalized before broader implementation.
- The approved mockup is directional but is not stored as a versioned artifact in the referenced repository paths.
- Current API contracts do not provide raw document preview, protected correction values, mutation actions, or a dedicated session/tenant display endpoint.
- Lifecycle timelines may require a future additive read contract if current processing/workflow/audit records cannot be safely correlated.
- Client-side status counts or search can mislead if presented as global results rather than current-page projections.
- Production API/runtime and identity adapters remain unavailable, so early UI integration is necessarily local/demo or contract-fixture based.

## 25. Acceptance Criteria

- The FlowSync Document Intelligence boundary is separate from Competitor Price, Streamlit, and backend internals.
- The route, page, component, API-client, state, auth, tenant, privacy, and responsive models are explicit.
- Existing GET-only API contracts cover every enabled v0.17 view; unsupported features are visibly deferred.
- The approved mockup is documented as directional, not a backend or pixel-perfect contract.
- API authority and tenant/security boundaries cannot be bypassed by UI behavior.
- Implementation is divided into six narrow, independently verifiable phases.
- Planning changes documentation only.
