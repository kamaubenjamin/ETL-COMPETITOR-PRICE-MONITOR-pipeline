# Repository Roadmap

## Purpose

This roadmap captures the long-term platform vision, runtime architecture, milestone progress, and planned work for the ETL Banking repository. It is written for Copilot, Cline, ChatGPT, Codex, and future developers who need a single, repo-level planning document.

## Vision

Build a production-ready ETL platform for pricing intelligence, supplier/customer reconciliation, and ERP-ready master data matching. The platform should support deterministic runtime layers, explainable decisions, reusable workflow stages, and a path to operational deployment with strong documentation, testing, and governance.

Key vision elements:
- End-to-end runtime architecture from document ingestion to master data matching
- Deterministic, auditable extraction and matching logic
- Modularity for future review, ERP, and agent-based automation layers
- Platform maturity aimed at v1.0 production deployment

## Runtime Architecture

The runtime stack is organized as a layered execution platform:

1. Document Runtime
2. Structural Runtime
3. Validation Runtime
4. Workflow Runtime
5. Entity Runtime
6. Matching Runtime
7. Review Runtime
8. ERP Runtime
9. Agent Runtime

Each runtime layer has a specific responsibility and clearly defined boundary, enabling incremental delivery and future extension.

## Completed Milestones

### Document Runtime

Purpose:
- Parse source documents and produce normalized document artifacts
- Extract sections, OCR/text, tables, and metadata for downstream processing

Delivered capabilities:
- Document ingestion pipeline
- Parsing and structure extraction
- Normalized document output for runtime consumption

### Workflow Runtime

Purpose:
- Execute stage-based ETL pipelines with configurable workflow definitions
- Orchestrate runtime stages such as extraction and matching

Delivered capabilities:
- Workflow stage registration and execution
- Stage dependency resolution
- Support for `entity_extract` and future runtime stages

### Entity Runtime

Purpose:
- Convert Document Runtime output into immutable entity contracts
- Validate, normalize, and score extracted business entities

Delivered capabilities:
- `EntityExtractionEngine` and package-level extraction architecture
- Immutable entity contracts in `src/entity_runtime/contracts`
- Validation, normalization, and confidence scoring modules
- Workflow integration via `entity_extract` stage

### Architecture Completion

Purpose:
- Establish baseline architecture coverage across major runtime boundaries
- Provide ADR records and onboarding documentation for future development
- Ensure runtime ownership and dependency direction are documented

Completed items:
- Workflow Runtime Architecture
- Entity Runtime Architecture
- Matching Runtime Architecture
- Document Runtime Architecture
- API Runtime Architecture
- Review Runtime Architecture
- Contract Registry v1 Architecture
- Runtime Boundaries document
- Agent onboarding context

## Latest Delivery

### v0.6 Extraction & Transformation Capability Hardening

Status:
- Closed and tagged as `v0.6-extraction-transformation-capability-hardening`
- Full regression and runtime-boundary verification pass

Delivered capabilities:
- Versioned deterministic transformation, mapping, validation, sorting, and aggregation contracts
- Real Workflow Runtime `transform`, `validate_data`, `sort`, and `aggregate` behavior
- Authoritative workflow stage catalog aligned with runtime registration and validation
- Privacy-safe metadata, immutable inputs, deterministic integration coverage, and legacy rule compatibility

References:
- `docs/architecture/EXTRACTION_TRANSFORMATION_CAPABILITY_HARDENING_V1_SUMMARY.md`
- `docs/architecture/EXTRACTION_TRANSFORMATION_CAPABILITY_HARDENING_V1_HANDOFF.md`
- `docs/adr/ADR-012-extraction-transformation-capability-hardening.md`
- `docs/releases/v0.6-extraction-transformation-capability-hardening.md`

### v0.7 Review / Correction Runtime

Status:
- Closed and tagged as `v0.7-review-correction-runtime`

Delivered capabilities:
- Deterministic review case lifecycle and reviewer decisions
- Field-level, version-aware corrections with append-only audit and lineage
- Non-blocking declarative reprocess requests and dry-run plans; execution remains Workflow-owned and deferred
- Backend source of truth for future Streamlit and FlowSync consumers

References:
- `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_PLAN.md`
- `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_SUMMARY.md`
- `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_HANDOFF.md`
- `docs/adr/ADR-013-review-correction-runtime.md`
- `docs/releases/v0.7-review-correction-runtime.md`

### v0.8 Document Intelligence Operator Console

Status:
- Closed and tagged as `v0.8-document-intelligence-operator-console`
- Live backend integration remains deferred to v0.9 and later milestones

Delivered capabilities:
- Separate Document Intelligence console beside the legacy competitor-price dashboard
- Operational overview, inbox, upload placeholder, processing, validation, matching, review, workflow, and audit views
- Display-only document and review lifecycle filters with no runtime mutation
- Local provider adapters, stable view models, reusable display components, and focused UI tests
- Review Queue and Audit Logs shaped from deterministic public Review Runtime contracts
- Consistent navigation, grouped workloads, status/priority labels, run-mode messaging, and filtered empty states
- No API, database, external service, OCR, or LLM dependency

References:
- `docs/architecture/DOCUMENT_INTELLIGENCE_OPERATOR_CONSOLE_V1_PLAN.md`
- `docs/architecture/DOCUMENT_INTELLIGENCE_OPERATOR_CONSOLE_V1_SUMMARY.md`
- `docs/architecture/DOCUMENT_INTELLIGENCE_OPERATOR_CONSOLE_V1_HANDOFF.md`
- `docs/releases/v0.8-document-intelligence-operator-console.md`

### v0.9 Document Intelligence API Foundation

Status:
- Architecture, implementation plan, and ADR complete
- Closed and tagged as `v0.9-document-intelligence-api-foundation`

Planned capabilities:
- Separate versioned read-only Document Intelligence API
- Health, document, processing, validation, matching, review, correction-history, reprocess-plan, workflow, and audit endpoints
- Deterministic providers and strict privacy-safe response contracts
- Streamlit API-provider preview and future FlowSync Document Intelligence consumer boundary
- R05-compliant integration through a future Workflow Runtime query facade

References:
- `docs/architecture/DOCUMENT_INTELLIGENCE_API_FOUNDATION_V1_PLAN.md`
- `docs/architecture/DOCUMENT_INTELLIGENCE_API_FOUNDATION_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/DOCUMENT_INTELLIGENCE_API_FOUNDATION_V1_SUMMARY.md`
- `docs/architecture/DOCUMENT_INTELLIGENCE_API_FOUNDATION_V1_HANDOFF.md`
- `docs/adr/ADR-014-document-intelligence-api-foundation.md`
- `docs/releases/v0.9-document-intelligence-api-foundation.md`

### v0.10 Workflow Query Facade

Status:
- Architecture, implementation plan, ADR, verification, summary, handoff, and release notes complete
- Closed and tagged as `v0.10-workflow-query-facade`

Planned capabilities:
- Workflow-owned public read facade under `src/workflow_runtime/query_facade/`
- Stable bounded read models for documents, processing, validation, matching, reviews, corrections, reprocess plans, workflow runs, and audit
- Deterministic in-memory facade and explicit API provider adapter
- Unchanged v0.9 API routes, envelopes, privacy behavior, pagination, and GET-only surface
- Narrow injected source ports with no direct cross-runtime implementation imports

References:
- `docs/architecture/WORKFLOW_QUERY_FACADE_V1_PLAN.md`
- `docs/architecture/WORKFLOW_QUERY_FACADE_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/WORKFLOW_QUERY_FACADE_V1_SUMMARY.md`
- `docs/architecture/WORKFLOW_QUERY_FACADE_V1_HANDOFF.md`
- `docs/adr/ADR-015-workflow-query-facade.md`
- `docs/releases/v0.10-workflow-query-facade.md`

### v0.11 Persistent Document State / Repository Layer

Status:
- Closed and tagged: `v0.11-persistent-document-state`
- All five phases complete: immutable contracts, deterministic in-memory repositories, a read-only Workflow Query Facade repository adapter, boundary/privacy/repository hardening, and release handoff

Planned capabilities:
- Persistence-neutral operational document state under `src/document_state/`
- Immutable records and explicit read/write repository ports for document, lifecycle, processing, validation, matching, review, correction, reprocess, workflow, and audit state
- Deterministic in-memory repositories with bounded pagination, stable ordering, idempotency, and optimistic version checks
- Injected repository adapter implementing public Workflow Query Facade ports
- Privacy-safe persistence with no raw document rows, correction values, artifact payloads, stack traces, or unrestricted metadata
- Unchanged v0.9 API contracts and v0.10 Query Facade read models

References:
- `docs/architecture/PERSISTENT_DOCUMENT_STATE_V1_PLAN.md`
- `docs/architecture/PERSISTENT_DOCUMENT_STATE_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/PERSISTENT_DOCUMENT_STATE_V1_SUMMARY.md`
- `docs/architecture/PERSISTENT_DOCUMENT_STATE_V1_HANDOFF.md`
- `docs/adr/ADR-016-persistent-document-state.md`
- `docs/releases/v0.11-persistent-document-state.md`

### v0.12 Durable Document State

Status:
- Closed and tagged as `v0.12-durable-document-state`
- Phase 1 implemented: persistence configuration, safe errors, deterministic schema metadata, and immutable migration/ledger validation contracts
- Phase 2 implemented: file-backed SQLite repositories, explicit relational schema, transactional migrations, optimistic updates, append idempotency, and reopen durability
- Phase 3 implemented: shared in-memory/SQLite conformance, rollback and snapshot consistency, migration replay, and deterministic basic writer concurrency verification
- Phase 4 implemented: explicit validated in-memory/SQLite composition with separate read/write surfaces and no silent fallback or automatic consumer wiring
- Phase 5 completed: release verification, summary, handoff, release notes, roadmap, debt, plan, ADR, and changelog closure

Planned capabilities:
- SQLite-backed local/dev durable repositories behind existing Document State ports
- Explicit relational schema and checksum-verified migration layout for all ten record families
- Transactional optimistic versioning and append idempotency
- Deterministic indexed filtering, ordering, and bounded pagination
- Shared in-memory/SQLite repository conformance tests
- Explicit in-memory versus SQLite repository selection with no silent fallback
- PostgreSQL production target and Supabase managed option deferred to later implementation
- Unchanged API, Query Facade, and Streamlit contracts and boundaries

References:
- `docs/architecture/DURABLE_DOCUMENT_STATE_V1_PLAN.md`
- `docs/architecture/DURABLE_DOCUMENT_STATE_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/DURABLE_DOCUMENT_STATE_V1_SUMMARY.md`
- `docs/architecture/DURABLE_DOCUMENT_STATE_V1_HANDOFF.md`
- `docs/adr/ADR-017-durable-document-state.md`
- `docs/releases/v0.12-durable-document-state.md`

### v0.13 Upload-to-Processing Writer Integration

Status:
- Architecture plan, implementation plan, and ADR accepted
- Closed and tagged as `v0.13-upload-processing-writer-integration`
- Phase 1 implemented: immutable writer commands, safe errors/results, deterministic idempotency helpers, fixed mapping catalog, and structural internal writer ports
- Phase 2 implemented: injected ingestion writer with idempotent document/lifecycle/audit behavior, optimistic classification snapshots, partial retry continuation, and in-memory/SQLite parity
- Phase 3 implemented: processing, validation, matching, review, correction, reprocess, workflow, lifecycle, and audit writers with optimistic versions, append idempotency, and backend parity
- Phase 4 implemented: full writer-to-Query-Facade/API-provider read-after-write verification, backend equivalence, SQLite reconstruction, replay, filters, pagination, privacy, and GET-only compatibility
- Phase 5 completed: release verification, summary, handoff, release notes, roadmap, debt, plan, ADR, and changelog closure

Planned capabilities:
- Runtime-neutral internal Document State writer commands and services
- Producer-side ingestion, workflow, validation, matching, and review adapters
- Deterministic create retry, append idempotency, and optimistic version behavior
- Privacy-safe opaque artifact references without raw payload storage
- In-memory and SQLite writer parity
- Read-after-write verification through Workflow Query Facade and existing API provider shapes
- No public mutation endpoints, UI writes, production activation, or silent backend fallback

References:
- `docs/architecture/UPLOAD_PROCESSING_WRITER_INTEGRATION_V1_PLAN.md`
- `docs/architecture/UPLOAD_PROCESSING_WRITER_INTEGRATION_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/UPLOAD_PROCESSING_WRITER_INTEGRATION_V1_SUMMARY.md`
- `docs/architecture/UPLOAD_PROCESSING_WRITER_INTEGRATION_V1_HANDOFF.md`
- `docs/adr/ADR-018-upload-processing-writer-integration.md`
- `docs/releases/v0.13-upload-processing-writer-integration.md`

### v0.14 Lifecycle Snapshot Advancement

Status:
- Architecture plan, implementation plan, and ADR-019 created
- Phase 1 implemented: immutable lifecycle transition/recovery contracts, stable results/errors, existing-status policy catalog, deterministic candidate ordering, privacy validation, and boundary tests
- Phase 2 implemented: repository-injected lifecycle advancement service with replay no-op, optimistic document updates, safe conflict/projection-pending/error mapping, and in-memory/SQLite verification
- Phase 3 implemented: optional writer integration with policy prevalidation, idempotent append, projection advancement, replay repair, explicit status allowlists, and legacy compatibility
- Phase 4 implemented: in-memory/SQLite read-after-advance verification through the Query Facade and API provider, including SQLite reconstruction, replay repair, filters, pagination, privacy, and GET-only compatibility
- Phase 5 completed: focused/full verification, summary, handoff, release notes, roadmap, debt, plan, ADR, and changelog closure
- Closed and tagged as `v0.14-lifecycle-snapshot-advancement`

Planned capabilities:
- Dedicated Document State lifecycle policy and advancement service
- Explicit allowed, terminal, failure, replay, and reprocess recovery transitions
- Optimistic `DocumentRecord` status/current-stage/version advancement
- Shared integration across v0.13 writer services
- In-memory/SQLite parity and read-after-advance verification
- Updated Query Facade/API/Streamlit status through existing read contracts
- No endpoint, UI, public mutation, backend-selection, OCR, LLM, or external-service changes

References:
- `docs/architecture/LIFECYCLE_SNAPSHOT_ADVANCEMENT_V1_PLAN.md`
- `docs/architecture/LIFECYCLE_SNAPSHOT_ADVANCEMENT_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/LIFECYCLE_SNAPSHOT_ADVANCEMENT_V1_SUMMARY.md`
- `docs/architecture/LIFECYCLE_SNAPSHOT_ADVANCEMENT_V1_HANDOFF.md`
- `docs/adr/ADR-019-lifecycle-snapshot-advancement.md`
- `docs/releases/v0.14-lifecycle-snapshot-advancement.md`

### v0.15 Auth / Tenants / Permissions

Status:
- Architecture plan, implementation plan, and ADR-020 created
- Phase 1 implemented: provider-neutral security contracts, exact permission/role catalogs, explicit principal types, authorization context/decisions, privacy-safe errors, and pure default-deny tenant policy
- Phase 2 implemented: identity-provider Protocol/results, explicit local demo/test provider, bounded authorization requests, and a pure policy-backed permission guard
- Phase 3 implemented: tenant/ownership fields on `DocumentRecord`, optional tenant-narrowed in-memory/SQLite and Query Facade document reads, additive SQLite migration `002`, and unchanged API payloads
- Phase 4 implemented: explicit API auth modes, provider-neutral identity resolution, centralized GET-route permission guards, tenant-narrowed provider reads, safe 401/403/404 behavior, and unchanged default local preview
- Phase 5 implemented: optional allowlisted local-demo identity headers for Streamlit `api_preview`, fixed privacy-safe auth/unavailable states, unchanged default `local_preview`, and API-authoritative permission enforcement
- Phase 6 completed: focused/full verification, boundary confirmation, summary, handoff, release notes, roadmap, debt, plan, ADR, and changelog closure
- Implemented, verified, closed, and tagged as `v0.15-auth-tenant-permission-boundaries`

Planned capabilities:
- Provider-neutral `src/security/` identity and authorization boundary
- Immutable principal, tenant, role, permission, resource-scope, context, decision, and actor-attribution contracts
- Default-deny tenant isolation with explicit platform-admin cross-tenant intent
- Scoped service-account and explicit system-actor identities
- Reusable API guards without inline route permission logic
- Tenant-aware Document State and Workflow Query Facade migration strategy
- Security-aware writer command gateway and audit attribution planning
- Deterministic local/test identities with production fail-closed behavior
- Future Supabase/PostgreSQL adapters without core provider coupling
- No public mutations, UI changes, migrations, dependencies, OCR, LLM, or external-service implementation during planning

Delivered phases:
1. Security contracts and role catalog
2. Policy engine and permission guards
3. Tenant-aware Document State and Query Facade contracts
4. Read-only API guard integration
5. Streamlit auth-mode preview
6. Security verification, documentation, and release closure

References:
- `docs/architecture/AUTH_TENANT_PERMISSION_MODEL_V1_PLAN.md`
- `docs/architecture/AUTH_TENANT_PERMISSION_MODEL_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/AUTH_TENANT_PERMISSION_MODEL_V1_SUMMARY.md`
- `docs/architecture/AUTH_TENANT_PERMISSION_MODEL_V1_HANDOFF.md`
- `docs/adr/ADR-020-auth-tenant-permission-boundaries.md`
- `docs/releases/v0.15-auth-tenant-permission-boundaries.md`

### v0.16 Production Composition / Runtime Selection

Status:
- Architecture plan, implementation plan, and ADR-021 created
- Phase 1 implemented: fixed runtime/backend/auth/identity/API/Streamlit modes, immutable redacted configuration, safe validation errors/results, pure compatibility helpers, deterministic matrix tests, and production fail-closed behavior
- Phase 2 implemented: validated in-memory/SQLite Document State composition, shared lifecycle advancement, four lifecycle-aware writers, Query Facade wiring, tenant-safe reads, redacted diagnostics, and no fallback
- Phase 3 implemented: API-owned runtime/config activation, app-scoped facade provider and auth composition, disabled/local-demo mapping, tenant-safe reads, compatibility fallback, and fail-closed unsupported auth
- Phase 4 implemented: non-authoritative Streamlit runtime/backend/auth labels, preserved API URL and identity preview, fixed safe runtime/auth/error states, and unchanged local preview default
- Phase 5 implemented: exhaustive production/deferred-backend rejection, composition invariants, precomposed-config revalidation, app/provider isolation, recursive import enforcement, and privacy-safe failure verification
- Phase 6 implemented: focused/full verification, summary, handoff, release notes, closure records, and owner tag recommendation
- Milestone implemented, verified, closed, and tagged as `v0.16-production-composition-runtime-selection`

Planned capabilities:
- Explicit `local`, `test`, `demo`, `local_api_auth`, `pilot`, and `production` runtime modes
- Immutable safe configuration loaded from an explicitly supplied allowlisted mapping
- Fixed runtime/backend/auth/identity/Streamlit compatibility matrix
- Outer `src/platform_runtime/` composition root with one-way dependency boundaries
- Explicit Document State in-memory/SQLite selection with no fallback
- Lifecycle advancement and all four writer services wired from composed repository ports
- Document State Query Facade adapter and facade-backed API provider composition
- App-scoped API provider/auth dependency injection without route or payload changes
- Non-authoritative Streamlit runtime/provider selection
- Production fail-closed behavior while PostgreSQL and real identity providers remain deferred
- Secret, path, DSN, credential, and raw-config redaction

Proposed phases:
1. Runtime mode/config contracts and validation matrix
2. Document State, Query Facade, lifecycle, and writer composition
3. API app/provider/auth composition activation
4. Streamlit runtime selection and safe config preview
5. Production fail-closed verification and boundary hardening
6. Release closure, handoff, and tag recommendation

References:
- `docs/architecture/PRODUCTION_COMPOSITION_RUNTIME_SELECTION_V1_PLAN.md`
- `docs/architecture/PRODUCTION_COMPOSITION_RUNTIME_SELECTION_V1_IMPLEMENTATION_PLAN.md`
- `docs/adr/ADR-021-production-composition-runtime-selection.md`

### v0.17 FlowSync Document Intelligence UI

Status:
- Architecture plan, implementation plan, and ADR-022 created
- Phase 1 implemented: isolated Vite/React/TypeScript app, enterprise shell, route metadata, safe placeholders, GET-only API client contracts, strict envelope parsing, fixed safe errors, and semantic theme foundations
- Phase 2 implemented: API-backed read-only document dashboard/detail, safe filters and current-result search, status metrics, stable table/detail projections, processing history, validation/matching summaries, fixed safe states, and no fixture fallback
- Phase 3 implemented: read-only validation/matching quality views, review queue/detail summaries, workflow activity, allowlisted audit events, strict payload projection, and reusable confidence/severity/priority/timeline presentation
- Phase 4 implemented: normalized auth/access/unavailable/malformed request states, fixed non-reflective messages, API-enforced visibility notices, and display-only runtime guidance with no frontend permission logic
- Phase 5 implemented: lockfile-backed advisory-free dependencies, strict typecheck/build, desktop/mobile and deep-link rendered smoke, safe no-API startup, keyboard skip navigation, and generated-output tracking guards
- Phase 6 completed: focused verification, summary, handoff, release notes, closure records, and owner tag recommendation
- Milestone implemented, verified, closed, and tagged as `v0.17-flowsync-document-intelligence-ui`
- Approved visual mockup recorded as directional product/design reference

Planned capabilities:
- Independent FlowSync Document Intelligence product boundary, separate from Competitor Price and Streamlit
- Enterprise app shell with sidebar, safe user/workspace context, and responsive navigation
- Read-only document dashboard, detail, processing/lifecycle, validation, matching, review, workflow, and audit views
- GET-only Document Intelligence API client with strict envelope, pagination, filter, and error handling
- API-authoritative authentication, tenant scope, permissions, and resource visibility
- Explicit loading, empty, unauthorized, forbidden, concealed-not-found, unavailable, and malformed-response states
- Semantic design tokens and reusable accessible components aligned to the approved mockup direction
- Future placeholders, but no enabled upload, correction, decision, reprocess, workflow, or export mutations

Proposed phases:
1. UI boundary, app shell, route contracts, API client contracts, and host/toolchain confirmation
2. Document list/detail read-only views
3. Validation, matching, review, workflow, and audit read-only views
4. Auth/tenant-aware UI states and unavailable/error hardening
5. Product polish, accessibility, responsive tests, and integration verification
6. Release closure, handoff, and tag recommendation

References:
- `docs/architecture/FLOWSYNC_DOCUMENT_INTELLIGENCE_UI_V1_PLAN.md`
- `docs/architecture/FLOWSYNC_DOCUMENT_INTELLIGENCE_UI_V1_IMPLEMENTATION_PLAN.md`
- `docs/adr/ADR-022-flowsync-document-intelligence-ui-boundary.md`

### v0.18 Export Runtime / ERP Integration Boundary

Status:
- Architecture plan, implementation plan, and ADR-023 created
- Phase 1 implemented: standard-library-only export catalogs, immutable readiness/payload/attempt/result/lifecycle/audit contracts, deterministic payload fingerprints/idempotency keys, privacy-safe errors, and structural adapter port
- Phase 2 implemented: deterministic safe-command payload builder, pure normalization, domain-separated canonical fingerprints, idempotency policy, privacy rejection, and `payload_invalid` readiness linkage
- Phase 3 implemented: persistence-neutral attempt/result repository Protocols, bounded deterministic queries, privacy-safe errors, lock-protected in-memory store, optimistic status updates, atomic duplicate claims, and immutable terminal results
- Phase 4 implemented: injected internal export service, safe command/result contracts, no-I/O success/failure/unavailable placeholders, duplicate blocking, stored terminal results, and returned audit/lifecycle intents
- Phase 5 implemented: safe export-history GET contracts, always-disabled prepare/export POST contracts, and read-only FlowSync readiness/history placeholder
- Phase 6 completed: focused/full verification, boundary confirmation, summary, handoff, release notes, closure records, and owner tag recommendation
- Milestone implemented, verified, and closed pending owner tag `v0.18-export-runtime-erp-integration-boundary`
- No real adapter, audit/lifecycle writer, enabled mutation, migration, dependency, external I/O, or ERP connection added

Planned capabilities:
- Independent `src/export_runtime/` policy and orchestration boundary
- Deterministic export readiness, sanitized payload, idempotency, attempt/result, audit, retry, and lifecycle contracts
- Atomic duplicate prevention and explicit unknown-delivery reconciliation
- Isolated CSV/ERP placeholder adapters behind `ExportAdapterPort`
- Default-deny `document:export`, tenant scope, service-account scope, and explicit cross-tenant controls
- Lifecycle advancement to `exported` only after recorded confirmed success
- Future authenticated API mutation boundary and disabled/read-only FlowSync export presentation

Proposed phases:
1. Export runtime contracts and status/readiness model
2. Export payload builder and idempotency policy
3. Export attempt/result repository integration
4. Export service with placeholder adapters and lifecycle/audit integration
5. API mutation contract boundary and FlowSync export-readiness placeholders, gated by owner approval
6. Verification, closure, handoff, and tag recommendation (complete pending owner tag)

References:
- `docs/architecture/EXPORT_RUNTIME_ERP_INTEGRATION_BOUNDARY_V1_PLAN.md`
- `docs/architecture/EXPORT_RUNTIME_ERP_INTEGRATION_BOUNDARY_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/EXPORT_RUNTIME_ERP_INTEGRATION_BOUNDARY_V1_SUMMARY.md`
- `docs/architecture/EXPORT_RUNTIME_ERP_INTEGRATION_BOUNDARY_V1_HANDOFF.md`
- `docs/adr/ADR-023-export-runtime-erp-integration-boundary.md`
- `docs/releases/v0.18-export-runtime-erp-integration-boundary.md`

### v0.19 Upload + Processing Activation

Status:
- Architecture plan, implementation plan, and ADR-024 created
- Phase 1 implemented: immutable upload contracts, validation policy/issues/results, safe command/result/error models, deterministic SHA-256 idempotency keys, opaque artifact references, and structural staging port
- Phase 2 implemented: API-authoritative permission/tenant guard, strict JSON metadata validation, safe tenant-filtered upload summary reads, and always-disabled staging response
- Phase 3 implemented: validated opaque-artifact activation, deterministic processing and received-document intents, safe receipts/results, and injected ingestion/Document State adapter ports with test-local fakes
- Phase 4 implemented: immutable progress read models, deterministic stage/percentage projections, tenant-scoped bounded queries, and guarded upload/document processing-status API reads
- Phase 5 implemented: FlowSync guarded metadata preview, recent uploads, API-supplied timeline, document processing-status panel, responsive states, and no-content-transmission checks
- Phase 6 completed: summary, handoff, release notes, verification record, closure alignment, and owner tag recommendation
- Milestone implemented, verified, and closed pending owner tag `v0.19-upload-processing-activation`
- No multipart bytes, migration, dependency, storage adapter implementation, concrete ingestion/Document State adapter, OCR/LLM, export activation, or ERP connection added

Planned capabilities:
- Standard-library-first upload contracts, validation, commands, safe results/errors, and narrow ports
- API-authoritative JSON metadata preview gated by authenticated tenant scope and `document:ingest`; multipart remains deferred
- Allowlisted PDF, CSV, XLSX, TXT, and EML evaluation with bounded filename/type/size/content checks
- Private opaque artifact staging into the existing deterministic ingestion pipeline
- Existing Document State ingestion/processing writers and lifecycle advancement integration
- Tenant-scoped upload history and processing progress projections
- FlowSync guarded upload surface and API-backed processing timeline preserving v0.17 identity
- Explicit no-export, no-ERP, no-OCR/LLM behavior

Proposed phases:
1. Upload contracts, validation, and command model
2. Guarded API upload boundary
3. Ingestion and Document State writer integration
4. Processing status/progress read models (complete)
5. FlowSync upload UI and processing timeline (complete)
6. Verification, closure, handoff, and tag recommendation

References:
- `docs/architecture/UPLOAD_PROCESSING_ACTIVATION_V1_PLAN.md`
- `docs/architecture/UPLOAD_PROCESSING_ACTIVATION_V1_IMPLEMENTATION_PLAN.md`
- `docs/adr/ADR-024-upload-processing-activation-boundary.md`
- `docs/architecture/UPLOAD_PROCESSING_ACTIVATION_V1_SUMMARY.md`
- `docs/architecture/UPLOAD_PROCESSING_ACTIVATION_V1_HANDOFF.md`
- `docs/releases/v0.19-upload-processing-activation.md`

### v0.20 Business Workflow / Rules Studio

Status:
- Architecture plan, seven-phase implementation plan, and ADR-025 created
- Phase 1 implemented: immutable Workflow Studio contracts, fixed statuses, safe structured rules/conditions/actions, privacy-safe metadata/errors, structural ports, and deterministic in-memory operation catalog
- Phase 2 implemented: deterministic validation results/service, dependency and cycle analysis, condition/path checks, catalog compatibility/readiness gates, and report-only legacy compatibility classification
- Phase 3 implemented: tenant-scoped process-local repositories, optimistic revisions, explicit draft/version transitions, immutable history, governed-definition publication/deactivation/archive policy, and safe audit intents
- Phases 1-3 focused verification passed with 147 tests; Phases 4-7 have not started
- Existing Workflow Runtime remains the sole execution authority
- Recommended independent `workflow_studio` governance package above the runtime
- No durable repository, runtime publication activation, preview, endpoint, UI behavior, permission, migration, dependency, OCR/LLM, ERP/export, upload-staging, or production execution change added

Planned capabilities:
- Immutable tenant-scoped workflow, rule, condition, action, version, validation, preview, publication, and audit contracts
- Explicit Studio operation catalog mapped only to proven existing runtime capabilities
- Schema, semantic, dependency/DAG, runtime-compatibility, security, and publication validation
- Editable drafts, immutable published versions, approval, deactivation, archive, and lineage-preserving rollback
- Bounded deterministic dry runs over approved fixtures or privacy-checked samples with no production side effects
- Controlled legacy Sanifu/Docsift translation proposals and per-operation migration reports
- Guarded Workflow Management API with dedicated permission evaluation and optimistic concurrency
- Structured FlowSync Rules Studio preserving the approved visual identity and API authority
- Explicit prohibition of arbitrary code, shell, raw SQL, filesystem, unrestricted HTTP, secrets, direct ERP/export, and silent tenant-crossing operations

Phases:
1. Contracts, statuses, definitions, and operation catalog - implemented and focused verification passed
2. Validation engine, dependency checks, and legacy compatibility report - implemented and focused verification passed
3. Versioned repository, draft lifecycle, and publication policy - implemented and focused verification passed
4. Safe dry-run/test boundary and audit intents
5. Guarded Workflow Management API
6. FlowSync Rules Studio UI foundation
7. Verification, closure, handoff, and tag recommendation

References:
- `docs/architecture/BUSINESS_WORKFLOW_RULES_STUDIO_V1_PLAN.md`
- `docs/architecture/BUSINESS_WORKFLOW_RULES_STUDIO_V1_IMPLEMENTATION_PLAN.md`
- `docs/adr/ADR-025-business-workflow-rules-studio-boundary.md`

## Prior Milestone Context

### v0.5 Runtime Hardening

Status:
- Active milestone
- Contract Registry v1 is formally closed
- CI Contract Validation v1 is implemented
- Runtime Boundary Verification v1 (Tier 1) is completed
- ✅ **Workflow Runtime Locking v1 is completed**
- ✅ **Entity Runtime Concurrency Hardening is completed**
- Next objective: Observability Improvements

Completed foundation deliverables:
- Contract Registry v1 with JSON Schema Draft 07 contracts, fixtures, local validation tests, and standalone validation script
- CI Contract Validation v1 with a lightweight GitHub Actions workflow for contract tests and standalone validation
- Runtime Boundary Verification v1 — Tier 1 Static Import Isolation Analysis
  - `scripts/verify_boundaries.py`: AST-based scanner for R01-R05, R12
  - `tests/boundaries/`: 22-test suite, exemption registry with 4 legacy entries
  - 0 active violations (compliant)
  - See `docs/architecture/RUNTIME_BOUNDARY_VERIFICATION_V1_SUMMARY.md`
- **Workflow Runtime Locking v1** — database-backed row-level locking with execution leases, file-based fallback, idempotency keys for deduplication, and comprehensive test suite (158/158 passing)
  - See `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_SUMMARY.md`
  - See `docs/adr/ADR-008-workflow-runtime-locking.md`

Next planned objectives:
1. ✅ **Workflow Runtime Locking** (completed)
2. ✅ **Entity Runtime Concurrency Hardening** (completed)
3. Observability Improvements
4. Review Runtime Audit Linking
5. Runtime Boundary Verification Tier 2 & 3 (future)

### Matching Runtime

Status:
- Released as v0.4
- Architecture baseline coverage is complete, with practice documents in place
- Document-level strategy is defined in `docs/architecture/MATCHING_RUNTIME_V1_ARCHITECTURE.md`
- Implementation validated with `tests/test_matching_runtime.py`

Objectives:
- Reconcile extracted entities against master data sources
- Support exact, normalized, fuzzy, and historical matching strategies
- Compute deterministic, explainable confidence scores
- Return immutable match results with audit explanations

Planned deliverables:
- Completed in v0.4 Matching Runtime release

Dependencies:
- `Entity Runtime` output (`EntitySet`)
- `Workflow Runtime` stage orchestration
- Local or in-memory master data candidate sources

## Planned Milestones

### CI Contract Validation

Purpose:
- Enforce Contract Registry v1 through hosted PR and release validation.
- Prevent incompatible schema changes from merging without versioning and ADR review.

Delivered capabilities:
- CI job for `pytest tests/contracts -v`
- CI job or step for `python scripts/validate_contracts.py`
- Minimal dependency install for `pytest` and `jsonschema`

Deferred capabilities:
- Schema compatibility checks against a released baseline
- Governance check for MAJOR schema changes and ADR presence

Dependencies:
- Contract Registry v1 schemas and fixtures
- Existing validation script and contract test suite

Status:
- Implemented as CI Contract Validation v1

### Review Runtime

Purpose:
- Provide human-review and exception management for unmatched or low-confidence entities
- Support review workflows, manual corrections, and audit handoff

Expected capabilities:
- Review queue generation from match results
- Manual override and match correction support
- Audit trail capture for review decisions
- Integration with workflow stage results

Dependencies:
- `Matching Runtime` for match result generation
- `Workflow Runtime` for review stage orchestration
- `Entity Runtime` for entity provenance

### ERP Runtime

Purpose:
- Enable ERP integration for master data lookup and downstream posting
- Support ERP-specific source/target mappings without mutating source documents

Expected capabilities:
- ERP master data source adapters
- Read-only ERP reconciliation support in v1
- Configurable ERP metadata and source selection

Dependencies:
- `Matching Runtime` for entity-to-master reconciliation
- `Workflow Runtime` for ERP stage orchestration
- ERP connection configuration and secure credential handling

### Agent Runtime

Purpose:
- Support automated agent workflows and decision automation on top of runtime outputs
- Provide structured automation for notifications, alerts, and corrective actions

Expected capabilities:
- Agent orchestration layer for rule-driven actions
- Triggered workflows based on match and review outcomes
- Integration points for policy-driven automation

Dependencies:
- `Workflow Runtime` for stage execution and event handling
- `Matching Runtime` and `Review Runtime` for decision context
- Platform governance and security policies

## Next Milestones

- Implement v0.20 Business Workflow / Rules Studio through seven reviewed phases after owner approval
- Keep existing Workflow Runtime as execution authority and begin with contracts/catalog, not production execution or a visual canvas
- Close and tag v0.7 Review / Correction Runtime after the Phase 5 documentation commit
- Plan durable Review Runtime persistence and trusted service boundaries
- Workflow Runtime Locking
- Entity Runtime Concurrency Hardening
- Observability Improvements
- Review Runtime Audit Linking
- Monitoring Runtime Architecture
- ERP Runtime Architecture
- Agent Runtime Architecture

## Cross-Cutting Initiatives

## v0.18 Export Runtime / ERP Boundary

- Phases 1-4: internal contracts, payload policy, repositories, and placeholder service complete.
- Phase 5: guarded export API contracts and read-only FlowSync readiness/history placeholders implemented; mutation remains disabled.
- Phase 6: final verification and release closure completed; owner tag remains pending.

### Documentation

- Maintain architecture docs in `docs/architecture`
- Keep design docs aligned with runtime boundaries and current status
- Provide clear handoff guidance for future agents and developers

### Testing

- Add package-level and integration tests for runtime components
- Validate workflow stage behavior with `pytest` suites
- Keep deterministic behavior and contract boundaries covered

### Governance

- Define runtime boundaries and architecture decisions clearly
- Track milestone status and platform ownership
- Preserve design intent through documentation and review

### Security

- Avoid storing sensitive data in architecture docs
- Design future ERP and agent layers with secure configuration boundaries
- Keep runtime code separated from credential and external-service logic

### Release Management

- Use milestone-based delivery for runtime layers
- Validate completed features before advancing to the next milestone
- Keep roadmap aligned with production deployment goals

## Long-Term Goal

Path to v1.0 production deployment:

1. Finish `Matching Runtime` with deterministic, audited master data matching.
2. Complete v0.5 Runtime Hardening, starting with CI enforcement for Contract Registry v1.
3. Deliver `Review Runtime` for human exception handling and correction.
4. Build `ERP Runtime` for ERP source integration and reconciliation support.
5. Add `Agent Runtime` for automation, notification, and workflow orchestration.
6. Strengthen documentation, testing, and governance across runtime layers.
7. Validate end-to-end workflows with production-like data and regression suites.

The v1.0 goal is a stable, explainable ETL platform that can ingest documents, extract entities, reconcile against master data, and support governance-aware review and automation.
