Technical debt and missing test fixtures

## v0.20 Business Workflow / Rules Studio Planning

### Current Status

**Planning complete; implementation has not started.**

ADR-025 and the v0.20 plans select a separate `workflow_studio` governance package above the existing Workflow Runtime. The runtime remains execution authority. The Studio is responsible for safe definitions, operation descriptors, validation, drafts, immutable versions, approval/publication policy, bounded preview, legacy migration reports, and audit intents through narrow ports.

Debt and decisions intentionally retained for implementation phases:

- Exact compiler/mapping contract from fine-grained Studio actions to existing coarse runtime operations
- Which candidate actions have proven deterministic publishable runtime implementations
- Richer input/output schemas and field-path type propagation across stages
- Durable repository choice, transaction model, one-active-version constraint, and migration approval
- Environment promotion and distinction between publication and production execution activation
- Preview adapter fidelity, timeouts, cancellation, resource accounting, fixture ownership, and retention
- Tenant-safe master-data source ownership, snapshotting, and replay policy
- Approval separation policy for small teams and platform administrators
- Definition diff/redaction policy and audit retention
- Version numbering, archive retention, deactivation, and rollback operational semantics
- Permission-catalog expansion beyond existing `workflow:read` and `workflow:run`
- Legacy Sanifu/Docsift fixtures and operation-by-operation semantic equivalence decisions
- Live authenticated API/UI testing, deployment, monitoring, and operational runbooks
- Collaborative editing, comments, visual canvas, reusable subworkflows, and parameter libraries
- Semantic classification and all LLM assistance

Planning explicitly prohibits arbitrary code, eval/exec, shell, imports, raw SQL, unrestricted HTTP, filesystem access, direct database writes, arbitrary JavaScript, secrets, direct ERP/export, upload staging, OCR/LLM execution, automatic production publication, unbounded execution, plugins/marketplace, and silent legacy conversion.

Recommended implementation begins with immutable contracts and an explicit operation catalog, then validation/legacy reporting, version/publication policy, bounded preview, API, FlowSync, and closure. Do not start with a visual canvas or production execution binding.

### References

- `docs/architecture/BUSINESS_WORKFLOW_RULES_STUDIO_V1_PLAN.md`
- `docs/architecture/BUSINESS_WORKFLOW_RULES_STUDIO_V1_IMPLEMENTATION_PLAN.md`
- `docs/adr/ADR-025-business-workflow-rules-studio-boundary.md`

## v0.19 Upload + Processing Activation

### Current Status

**v0.19 is implemented, verified, and closed pending owner tag.**

ADR-024 and the v0.19 plans establish a separate transport-neutral upload policy boundary around existing deterministic ingestion and Document State writers. The API owns the current JSON metadata preview, authentication, tenant/permission gates, IDs, and safe envelopes. Future multipart/raw content may reach the path-based ingestion pipeline only through an approved private opaque staging boundary; FlowSync remains non-authoritative.

Debt intentionally retained:

- Production encrypted file/object storage, quarantine, retention, deletion, backup, recovery, and legal hold
- Malware scanning and content-disarm policy
- Async queue/outbox, workers, timeout ownership, retry, reconciliation, and partial-progress operations
- MIME/signature depth and decompression/resource-bomb protection
- EML attachment/header policy and legacy XLS activation
- Separate `document:upload` permission decision versus existing `document:ingest`
- Upload idempotency semantics for intentional identical re-uploads
- Production rate limiting, gateway/TLS/CORS, telemetry, alerts, and runbooks
- OCR/LLM, image/archive/batch/resumable upload, raw download, and protected preview
- Enabled export, upload-to-export automation, and ERP integration

These are deferred prerequisites or later product decisions, not planning omissions. No production upload should activate until the applicable security, storage, and operational items are resolved.

Phase 1 provides immutable upload contracts, deterministic validation and stable issue ordering, bounded scalar-only metadata, privacy-safe results/errors, opaque staging references, domain-separated idempotency keys, and a structural no-I/O staging port. It does not stage bytes, inspect signatures/content, call ingestion, persist state, expose API routes, or modify FlowSync. The focused Upload Runtime suite passes 46 tests.

Phase 2 provides metadata-only upload POST validation plus safe upload history/detail GET contracts. The API owns authentication, active tenant, actor, and `document:ingest` authorization; disabled mode and valid authorized requests both remain unable to stage. Multipart transport, raw bytes, storage, ingestion, Document State writes, processing activation, service-account production policy, and FlowSync remain deferred. The API suite passes 103 tests with 9 skips.

Phase 3 provides a no-I/O activation service over validated commands and opaque staged-artifact references, deterministic upload/document/source-event identities, safe processing and writer intents, structural ingestion/writer ports, fixed safe receipts/results, prerequisite ordering, and exception sanitization. Test-local fakes prove calls occur only after validation and artifact matching. Concrete artifact resolution, ingestion execution, Document State command mapping/lifecycle calls, durable state, API activation, and operational recovery remain deferred. Upload Runtime passes 62 tests; API passes 105 tests with 9 skips.

Phase 4 provides immutable safe progress read models, a separate capability-aligned read-status catalog, deterministic stage ordering and approximate percentage derivation, safe projections, tenant-scoped in-memory queries, and guarded upload/document progress API reads. The provider remains ephemeral; durable progress persistence, direct Query Facade/Document State adapters, and processing activation remain deferred. FlowSync presentation was delivered in Phase 5.

Phase 5 provides a FlowSync guarded metadata validation preview and read-only progress experience. The browser never reads or transmits selected document content; staging-disabled remains explicit, recent/progress/timeline data remains API-owned, and refresh is manual. Durable recent-upload data, populated event timelines, real staging/transport, processing activation, production authentication, polling/realtime updates, and operational retry remain deferred.

Phase 6 closes the milestone with architecture summary, handoff, release notes, aligned status records, verification evidence, explicit production-unavailable state, deferred-work ownership, recommended tag, and v0.20 handoff. The verified implementation baseline remains 1,777 passed and 9 skipped; FlowSync validation/typecheck/build passed and boundary verification is compliant. Closure changes documentation only.

## v0.18 Export Activation Deferred

Phase 5 deliberately exposes no executable export mutation. The POST contracts return `mutation_not_enabled`, the read provider is ephemeral and summary-only, and FlowSync is GET-only. Before activation, add authenticated production identity, exact tenant/resource authorization, durable attempt/result persistence, audit and lifecycle writers, target catalog ownership, approved adapter composition, reconciliation, rate limits, and operational controls.

## Extraction & Transformation Capability Hardening v1

### Current Status

**Closed and tagged as `v0.6-extraction-transformation-capability-hardening`.**

Delivered under `src/transforms/` and Workflow Runtime:

- Versioned transform, mapping, validation, sorting, and aggregation contracts
- Deterministic `transform`, `validate_data`, `sort`, and `aggregate` workflow stages
- Strict configuration validation, input immutability, bounded privacy-safe validation results, and deterministic integration coverage
- Legacy transformation compatibility and stage catalog/validator alignment

### Remaining Verification Debt

- The boundary verifier still skips `src/alerts/alert_engine.py` and `src/entity_runtime/engine.py` because of existing U+FEFF characters; these warnings predate v0.6 and should be corrected separately.

### Deferred Capability Debt

- Nested field mapping and persistent/external mapping registries
- Streaming or distributed transformation execution
- Pivoting, window functions, and time-series aggregation
- Full MDM/golden-record lifecycle and survivorship
- OCR and LLM-based extraction remain explicitly outside v0.6

### Reference

- `docs/architecture/EXTRACTION_TRANSFORMATION_CAPABILITY_HARDENING_V1_SUMMARY.md`
- `docs/architecture/EXTRACTION_TRANSFORMATION_CAPABILITY_HARDENING_V1_HANDOFF.md`
- `docs/releases/v0.6-extraction-transformation-capability-hardening.md`

---

## Review / Correction Runtime v1

### Current Status

**Closed and tagged as `v0.7-review-correction-runtime`.**

Resolved in v0.7:

- Canonical eight-state lifecycle and five reviewer decisions
- Field-addressed, lineage-aware controlled corrections
- Ordered append-only audit records for canonical services
- Idempotent creation, optimistic case versions, and declarative dry-run reprocess plans
- Bounded allowlisted metadata and privacy-safe errors/audit summaries

Remaining debt:

- Durable database persistence, atomic multi-process transactions, migrations, retention, and audit signing
- Authenticated/authorized reviewer identity and protected correction-value access
- Workflow review-stage adapter, reprocess acknowledgement, and execution
- Shared neutral stage catalog; the dry-run planner currently mirrors a local safe allowlist
- API, UI, Streamlit, FlowSync, notifications, and observability instrumentation
- Legacy prototype modules remain alongside canonical v1 services and need a future deprecation plan

Closure is documented in:

- `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_PLAN.md`
- `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_SUMMARY.md`
- `docs/architecture/REVIEW_CORRECTION_RUNTIME_V1_HANDOFF.md`
- `docs/adr/ADR-013-review-correction-runtime.md`
- `docs/releases/v0.7-review-correction-runtime.md`

---

## Document Intelligence Operator Console v1

### Current Status

**Closed and tagged as `v0.8-document-intelligence-operator-console`; live backend integration remains deferred.**

Remaining debt:

- Replace `LocalOperatorConsoleProvider` fixtures with bounded read-only application-service adapters behind the same display contract
- Replace constructed Review Runtime samples with an authorized read-only repository/service adapter
- Add authenticated operator identity and role-based authorization
- Add protected access rules for sensitive document and correction values
- Implement production upload through a backend-owned ingestion boundary
- Add command submission through runtime services with idempotency and optimistic versions
- Add accessibility, responsive-layout, deployment, and browser-level regression verification
- Validate status/priority labels with operators before treating the display vocabulary as a stable external contract
- Keep the legacy competitor-price `dashboard.py` separate until an explicit retirement milestone

References:

- `docs/architecture/DOCUMENT_INTELLIGENCE_OPERATOR_CONSOLE_V1_PLAN.md`
- `docs/architecture/DOCUMENT_INTELLIGENCE_OPERATOR_CONSOLE_V1_SUMMARY.md`
- `docs/architecture/DOCUMENT_INTELLIGENCE_OPERATOR_CONSOLE_V1_HANDOFF.md`
- `docs/releases/v0.8-document-intelligence-operator-console.md`

---

## Document Intelligence API Foundation v1

### Current Status

**v0.9 is closed and tagged as `v0.9-document-intelligence-api-foundation`.**

Planning resolves the API ownership direction but does not yet resolve:

- R05-compliant live query aggregation through a public Workflow Runtime facade
- Authentication, authorization, tenant isolation, rate limiting, and public deployment
- Durable runtime providers, caching, cursor pagination, or service-level objectives
- Mutation contracts for upload, corrections, decisions, reprocessing, and workflow execution
- Retirement of four legacy `src/api/app.py` boundary exemptions
- Production CORS, API gateway, TLS, observability, and operational support
- Declared test-client transport dependency alignment: the active Starlette build requires optional `httpx2`, which is not currently declared or installed

Phase 2 uses deterministic API-owned preview records only; replacement with a live R05-compliant query provider remains deferred.

Phase 3 adds an unauthenticated local/user-configured HTTP preview client. Production endpoint allowlisting, TLS policy, authentication, authorization, retry policy, and operational telemetry remain deferred; unavailable API mode intentionally does not fall back silently to local fixtures.

Phase 4 keeps CORS disabled and adds transport safety headers, safe global errors, and request-ID propagation. Production CORS origins, trusted hosts, TLS termination, authentication/authorization, tenant isolation, rate limiting, and request logging remain deliberate future security work.

References:

- `docs/architecture/DOCUMENT_INTELLIGENCE_API_FOUNDATION_V1_PLAN.md`
- `docs/architecture/DOCUMENT_INTELLIGENCE_API_FOUNDATION_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/DOCUMENT_INTELLIGENCE_API_FOUNDATION_V1_SUMMARY.md`
- `docs/architecture/DOCUMENT_INTELLIGENCE_API_FOUNDATION_V1_HANDOFF.md`
- `docs/adr/ADR-014-document-intelligence-api-foundation.md`
- `docs/releases/v0.9-document-intelligence-api-foundation.md`

---

## Workflow Query Facade v1

### Current Status

**v0.10 is closed and tagged as `v0.10-workflow-query-facade`.**

The planned facade resolves API dependency direction but deliberately does not yet resolve:

- Live runtime read adapters and the approved composition root that injects them
- Cross-source transactional snapshot consistency
- Durable/materialized read storage, migrations, retention, caching, or cursor pagination
- Authentication, authorization, tenant isolation, and policy-filtered live reads
- Rate limiting, production gateway/CORS/TLS, telemetry, and service-level objectives
- Mutation commands, workflow execution, idempotency, concurrency, and command audit
- FlowSync Document Intelligence production UI
- OCR, LLM processing, and external services

Guardrail: `src/workflow_runtime/query_facade/` must use narrow injected ports and must not become a location for direct imports of runtime repositories, stores, services, or models.

Phase 3 makes the deterministic facade-backed API provider preferred and retains the API-local provider for compatibility. This does not provide live operational reads; approved source adapters and a composition boundary remain deferred.

Phase 4 verifies the facade/API import boundary, payload compatibility, privacy projections, GET-only surface, request IDs, and security headers. Facade errors now map to bounded API `400`, `404`, `503`, and `500` outcomes without leaking source internals. Production identity, tenant policy, persistence, and live source availability semantics remain deferred.

References:

- `docs/architecture/WORKFLOW_QUERY_FACADE_V1_PLAN.md`
- `docs/architecture/WORKFLOW_QUERY_FACADE_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/WORKFLOW_QUERY_FACADE_V1_SUMMARY.md`
- `docs/architecture/WORKFLOW_QUERY_FACADE_V1_HANDOFF.md`
- `docs/adr/ADR-015-workflow-query-facade.md`
- `docs/releases/v0.10-workflow-query-facade.md`

---

## Persistent Document State v1

### Current Status

**v0.11 is closed and tagged as `v0.11-persistent-document-state`.**

The milestone plans persistence-neutral contracts and deterministic repositories but deliberately defers:

- Database engine, schemas, migrations, ORM/query tooling, and connection management
- Durable transactions, isolation, cross-repository snapshots, outbox delivery, backup, retention, and disaster recovery
- Production composition root and live ingestion/processing/review/workflow writer adapters
- Authentication, authorization, tenant partitioning, row-level policy, encryption, and key management
- Caching, cursor pagination, indexing, archival, telemetry, and service-level objectives
- Mutation endpoints, uploads, FlowSync Document Intelligence, OCR, LLM, and external services

Guardrails:

- API and Streamlit must continue to read through the Workflow Query Facade, never repositories.
- Core `src/document_state/` must remain independent of API, UI, runtime implementations, storage, telemetry, database, and competitor-price modules.
- Query-facing repositories must not store raw documents, rows, correction values, artifact payloads, stack traces, or arbitrary metadata.
- Deterministic in-memory repository behavior must not be represented as durable production persistence.

Phase 1 provides persistence-neutral contracts only: ten immutable record types, bounded pagination, fixed filters/orderings, safe coded errors, privacy allowlists, and separate structural read/write repository ports. It contains no repository implementation, database, migration, adapter, API/UI integration, or live writer.

Phase 2 provides deterministic process-local repositories only. Separate reader/writer views share lock-protected memory, writes revalidate immutable records, mutable snapshots enforce expected versions, and append-only records enforce stable-key idempotency. State is neither durable nor cross-process; database transactions, persistence, production composition, and live writers remain deferred.

Phase 3 provides a read-only adapter from injected Document State read repositories to public Workflow Query Facade models. It preserves facade filters, ordering, bounded pagination, safe errors, and privacy projections, but no production composition root selects it and no API or UI reads repositories directly.

Phase 4 verifies recursive import boundaries, API/UI isolation, privacy projection, immutable repository returns, safe error translation, optimistic conflicts, append idempotency conflicts, and absence of database/file/network access. This verification does not make the process-local repositories durable or production-ready.

Phase 5 closes the deterministic foundation with verified release documentation and handoff. Durable repositories, migrations, production composition, live writers, tenant/security policy, retention, encrypted blob storage, and mutation APIs remain explicit future debt.

References:

- `docs/architecture/PERSISTENT_DOCUMENT_STATE_V1_PLAN.md`
- `docs/architecture/PERSISTENT_DOCUMENT_STATE_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/PERSISTENT_DOCUMENT_STATE_V1_SUMMARY.md`
- `docs/architecture/PERSISTENT_DOCUMENT_STATE_V1_HANDOFF.md`
- `docs/adr/ADR-016-persistent-document-state.md`
- `docs/releases/v0.11-persistent-document-state.md`

---

## Durable Document State v1

### Current Status

**v0.12 is closed and tagged as `v0.12-durable-document-state`.**

The approved phased recommendation is SQLite for local/dev durability, PostgreSQL as the production target, and Supabase/Postgres as a possible future managed deployment. The milestone must preserve v0.11 repository interfaces and keep API/UI consumers behind the Workflow Query Facade.

Planned debt addressed by v0.12:

- Durable SQLite schema and ordered checksum-verified migrations
- File reopen/recovery verification without production infrastructure
- Transactional compare-and-swap version updates
- Database-enforced append idempotency and conflict behavior
- Indexed deterministic filters/orderings and bounded pagination
- Shared repository conformance across in-memory and SQLite implementations
- Explicit repository selection with no silent fallback

Phase 1 provides standard-library-only configuration contracts for `in_memory`, `sqlite`, and deferred `future_postgres`; seven privacy-safe persistence error codes; deterministic metadata for all planned durable tables; and immutable migration definition/applied-ledger contracts with duplicate, sequence, engine, and checksum-conflict validation. It opens no database, writes no file, and contains no SQL or repository implementation.

Phase 2 provides file-backed standard-library SQLite repositories for all ten record families, explicit-column schema storage, canonical validated metadata JSON, transactional checksum-ledger migrations, transaction-consistent count/page reads, compare-and-swap updates, append idempotency, deterministic ordering/filtering, and close/reopen durability.

Phase 3 provides a shared in-memory/SQLite repository contract suite plus deterministic SQLite rollback, read-snapshot, migration replay, durability, same-version writer, identical retry, and conflicting idempotency verification. No backend divergence or production-code defect was found. Composition selection, production-scale concurrency/load testing, PostgreSQL, backups, and production operations remain deferred.

Phase 4 provides explicit validated `in_memory` or `sqlite` selection through a frozen composition result with separate read/write repository surfaces. SQLite requires a file path and never falls back to memory; deferred/unknown backends fail closed. Application bootstrap activation, API/UI wiring, live writers, production-scale concurrency/load testing, PostgreSQL, backups, and production operations remain deferred.

Phase 5 confirms 175 Document State tests, 62 Query Facade tests, 245 API/UI/Review tests with 9 skips, and 1,159 full-regression tests with 9 skips. Boundary verification is compliant. The remaining items below are deferred product and production work rather than incomplete v0.12 scope.

Still deferred beyond v0.12:

- PostgreSQL repository and migration implementation, driver, pooling, provisioning, backup, and recovery
- Supabase integration, row-level security, and managed deployment policy
- Production composition default and live upload/processing writers
- Cross-record units of work, outbox delivery, and global snapshot consistency
- Authentication, authorization, tenant isolation, retention periods, archive execution, and encrypted raw blob storage
- Mutation endpoints, production telemetry, FlowSync Document Intelligence, OCR, LLM, and external services

References:

- `docs/architecture/DURABLE_DOCUMENT_STATE_V1_PLAN.md`
- `docs/architecture/DURABLE_DOCUMENT_STATE_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/DURABLE_DOCUMENT_STATE_V1_SUMMARY.md`
- `docs/architecture/DURABLE_DOCUMENT_STATE_V1_HANDOFF.md`
- `docs/adr/ADR-017-durable-document-state.md`
- `docs/releases/v0.12-durable-document-state.md`

---

## Upload-to-Processing Writer Integration v1

### Current Status

**v0.13 is closed and tagged as `v0.13-upload-processing-writer-integration`.**

Document State has durable local/dev repositories, explicit composition, and internal writer services that can populate all operational record families from normalized commands. Concrete upload, ingestion, workflow, validation, matching, and review producer adapters are not yet connected. API and Streamlit remain read-only and must not receive repository write ports.

Planned debt addressed by v0.13:

- Normalized internal writer commands instead of persisting runtime result payloads
- Deterministic ingestion create retries and append idempotency
- Explicit compare-and-swap version behavior for mutable snapshots
- Producer-side mapping for ingestion, workflow, validation, matching, review, correction, and reprocess outcomes
- Privacy-safe opaque artifact references with no raw payload storage
- Replay-safe handling of operation-level partial writes
- In-memory/SQLite writer parity and Query Facade/API read-after-write verification

Phase 1 provides immutable JSON-compatible commands for all planned writer domains, privacy-safe opaque artifact references, fixed coded errors and result statuses, hashed domain-separated idempotency keys, deterministic mapping definitions, and structural internal writer ports. It contains no repository calls, runtime adapters, API/UI integration, or persistence-engine imports.

Phase 2 provides an internal ingestion writer over explicitly injected read/write repository ports. Document create retries use safe read-compare-create, lifecycle/audit appends reuse deterministic repository idempotency, classification snapshots enforce expected versions, and operation-level partial retries resume without backend selection or API/UI coupling. Opaque artifact references are validated at the command boundary but remain outside current query-facing records because no artifact reference field has yet been approved for persistence.

Phase 3 provides internal processing, validation, matching, review, correction, reprocess, workflow-run, lifecycle, and audit writer services. Mutable snapshots use explicit versions and retry comparison; append-only records use domain-separated keys; batch failures return only bounded committed IDs and resume safely. The services remain backend-neutral and are not yet called by runtime producers.

Phase 4 verifies deterministic writer output through Document State repositories, `DocumentStateQueryFacadeAdapter`, the Workflow Query Facade port, and `FacadeDocumentIntelligenceProvider`. Both active backends produce equivalent projections, SQLite survives reconstruction, replay remains duplicate-free, filters/pagination remain correct, and v0.9 API shapes and GET-only routes remain unchanged. Direct runtime producer adapters are still deferred.

Phase 5 confirms 72 writer tests, 247 Document State tests, 45 API tests with 9 skips, 266 Query Facade/UI/Review tests, and 1,235 full-regression tests with 9 skips. Boundary verification is compliant. Release documentation explicitly records that the mutable document projection remains `received`; append-only lifecycle events do not yet advance it.

Still deferred beyond v0.13:

- Runtime producer adapters and application bootstrap injection
- Governed lifecycle-driven document snapshot advancement
- Cross-record unit-of-work and transactional outbox
- PostgreSQL/Supabase and production composition activation
- Public mutation endpoints and Streamlit write actions
- Authentication, authorization, tenant isolation, and rate limiting
- Raw encrypted blob storage, malware scanning, backup/recovery, retention/archive/legal hold
- Production telemetry, FlowSync Document Intelligence, OCR, LLM, and external services

References:

- `docs/architecture/UPLOAD_PROCESSING_WRITER_INTEGRATION_V1_PLAN.md`
- `docs/architecture/UPLOAD_PROCESSING_WRITER_INTEGRATION_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/UPLOAD_PROCESSING_WRITER_INTEGRATION_V1_SUMMARY.md`
- `docs/architecture/UPLOAD_PROCESSING_WRITER_INTEGRATION_V1_HANDOFF.md`
- `docs/adr/ADR-018-upload-processing-writer-integration.md`
- `docs/releases/v0.13-upload-processing-writer-integration.md`

---

## Lifecycle Snapshot Advancement v1

### Current Status

**v0.14 is closed and tagged as `v0.14-lifecycle-snapshot-advancement`.**

v0.13 lifecycle events are append-only and authoritative, but the mutable `DocumentRecord` remains at `received`. v0.14 plans a dedicated Document State lifecycle service that applies one explicit transition catalog and advances the projection through existing optimistic repository ports.

Planned debt addressed by v0.14:

- Central lifecycle graph instead of writer-specific or rank-based transition inference
- Deterministic status/current-stage/version advancement
- Same-event replay without duplicate version increments
- Safe stale-version, invalid-transition, missing-document, and source-unavailable behavior
- Linked reprocess recovery without treating a dry-run plan as execution
- In-memory/SQLite parity and Query Facade/API/Streamlit read-after-advance verification

Phase 1 provides immutable JSON-compatible transition, recovery, policy-decision, result, and error contracts; an explicit catalog over the existing `DocumentStatus` vocabulary; deterministic candidate ordering; same-state no-op behavior; terminal-state rejection; governed failed-state recovery; and recursive privacy/boundary tests. It does not call repositories, update documents, integrate writers, or implement the advancement service.

Phase 2 provides `LifecycleAdvancementService` over explicit narrow document read/write ports. It validates current state and expected version, applies policy, updates status/current stage/time/version through compare-and-swap, preserves metadata, maps repository failures safely, and distinguishes ordinary conflicts from projection-pending conflicts after an event append. Both active backends are verified; writer integration and automatic event append remain deferred.

Phase 3 integrates all four writer services through optional explicit lifecycle-service injection. The shared helper prevalidates policy, appends history idempotently, advances the snapshot with persisted-event context, reports projection-pending conflicts safely, and supports replay repair. Explicit processing/review/workflow status allowlists prevent inference and unsupported states. Legacy behavior remains unchanged without injection; application bootstrap and producer adapters remain deferred.

Phase 4 verifies read-after-advance through explicit in-memory and SQLite compositions, `DocumentStateQueryFacadeAdapter`, the structural Workflow Query Facade port, and `FacadeDocumentIntelligenceProvider`. SQLite state survives composition reconstruction; advanced-status filters, bounded pagination, replay no-op, projection repair, privacy projections, v0.9 provider shapes, and GET-only routes remain compatible. No production modules required modification.

Phase 5 confirms 63 lifecycle tests, 80 writer tests, 318 Document State tests, 48 API tests with 9 skips, 266 Query Facade/UI/Review tests, and 1,309 full-regression tests with 9 skips. Boundary verification is compliant. Remaining items below are deferred production and product work rather than incomplete v0.14 scope.

Still deferred beyond v0.14:

- Runtime producer adapters and production bootstrap activation
- Cross-record unit of work, transactional outbox, and background reconciliation
- Bulk historical projection rebuild/backfill
- Public mutation endpoints and upload UI/API
- Authentication, authorization, tenants, and production database activation
- New document-level skipped/cancelled disposition contracts
- Raw encrypted blob storage, FlowSync, OCR, LLM, and external services

References:

- `docs/architecture/LIFECYCLE_SNAPSHOT_ADVANCEMENT_V1_PLAN.md`
- `docs/architecture/LIFECYCLE_SNAPSHOT_ADVANCEMENT_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/LIFECYCLE_SNAPSHOT_ADVANCEMENT_V1_SUMMARY.md`
- `docs/architecture/LIFECYCLE_SNAPSHOT_ADVANCEMENT_V1_HANDOFF.md`
- `docs/adr/ADR-019-lifecycle-snapshot-advancement.md`
- `docs/releases/v0.14-lifecycle-snapshot-advancement.md`

---

## Auth, Tenant, And Permission Model v1

### Current Status

**v0.15 is implemented, verified, closed, and tagged.**

Current security debt:

- Document Intelligence API can resolve principals and enforce tenant-scoped GET reads when auth is explicitly enabled; default local preview remains intentionally unauthenticated.
- API providers accept guard-produced tenant scope for protected reads; production composition is not activated.
- Streamlit workspace selection remains display-only; `api_preview` can send one explicit allowlisted local-demo identity header, while the API remains authoritative.
- Child Document State records still lack direct tenant columns; the document projection now carries tenant, workspace, ownership, creator, and updater fields.
- Selected records carry actor IDs without verified principal/tenant attribution.
- Writers receive commands/repositories but no trusted authorization gateway or actor context.
- SQLite migration `002` scopes documents and backfills legacy rows to `tenant-local`; child-table tenant columns, PostgreSQL/Supabase, and row-level security are not implemented.

Phase 1 establishes the provider-neutral `src/security/` boundary with immutable contracts, exact role/permission catalogs, explicit anonymous/user/service/system principals, tenant and resource scopes, authorization contexts and decisions, privacy-safe errors, and pure default-deny policy evaluation. Security policy remains outside API routes, Streamlit, repositories, Query Facade logic, and writers.

Phase 2 adds a structural identity-provider boundary, privacy-safe resolution results, deterministic local demo/test identities, bounded authorization requests, and a reusable pure permission guard. The local provider rejects production mode and performs no token verification or environment mutation.

Phase 3 adds explicit document tenant/ownership fields, optional tenant-narrowed document get/list behavior across in-memory and SQLite repositories, tenant-aware Query Facade document contracts, and durable migration/index support. Unscoped local preview remains backward compatible, and existing API payloads exclude internal tenant fields.

Phase 4 adds explicit API auth modes, API-local identity/context composition, centralized endpoint permission declarations, safe identity-provider failure handling, and tenant-narrowed provider reads. Review and reprocess reads require `document:review`; workflow runs require `workflow:read`; audit events require `audit:read`. Authenticated cross-tenant detail denial is concealed as `404`.

Phase 5 adds a development-only Streamlit `api_preview` identity selector. It sends only an allowlisted local-demo identity header, never sends a tenant override or credential, and maps API failures to fixed safe display states. `local_preview` remains unchanged and default; Streamlit performs no permission decision or security filtering.

Phase 6 confirms 60 security tests, 59 API tests with 9 skips, 42 Streamlit tests, 330 Document State tests, 239 Query Facade/Review tests, and 1,408 full-regression tests with 9 skips. Boundary verification is compliant. Release documentation records current local compatibility and the remaining production-security work without overstating deployment readiness.

Remaining implementation is phased and deferred. No writer enforcement, child-record tenant migration, external identity-provider adapter, production activation, public mutation, credential/session management, or dependency has been added.

References:

- `docs/architecture/AUTH_TENANT_PERMISSION_MODEL_V1_PLAN.md`
- `docs/architecture/AUTH_TENANT_PERMISSION_MODEL_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/AUTH_TENANT_PERMISSION_MODEL_V1_SUMMARY.md`
- `docs/architecture/AUTH_TENANT_PERMISSION_MODEL_V1_HANDOFF.md`
- `docs/adr/ADR-020-auth-tenant-permission-boundaries.md`
- `docs/releases/v0.15-auth-tenant-permission-boundaries.md`

---

## Production Composition / Runtime Selection v1

### Current Status

**v0.16 is implemented, verified, closed, and tagged.**

Current composition debt:

- Internal Document State, lifecycle, writer, and Query Facade composition is owned by `src/platform_runtime/`; the API factory now activates it without making `platform_runtime` depend on FastAPI.
- Composed API routes resolve an app-scoped provider; the module-level deterministic facade provider remains only for backward-compatible default app creation.
- Runtime mode, backend, auth, identity provider, and Streamlit provider compatibility is represented by one immutable validated contract and fail-closed matrix.
- Production persistence and identity adapters do not exist, so production must remain deliberately unavailable.
- Pilot tenancy constraints remain unresolved while child Document State records lack direct tenant columns.
- Resource shutdown ownership is minimal for current local resources; production resource ownership and secret resolution remain deferred.

The v0.16 plan selects an outer `src/platform_runtime/` package with one-way imports into approved public boundaries. It defines explicit local/test/demo/local-API-auth/pilot/production modes, a strict backend/auth matrix, pure allowlisted config loading, lifecycle/writer/Query Facade wiring, app-scoped API provider injection, non-authoritative Streamlit selection, and production fail-closed behavior.

Production will reject startup until an implemented production PostgreSQL adapter and real identity provider are injected. It will never fall back to in-memory, SQLite, local identities, disabled auth, or local Streamlit preview.

Phase 1 provides only immutable configuration contracts and pure validation. It intentionally does not read environment variables, construct resources, wire services, activate API/Streamlit composition, or implement deferred adapters. Pilot is a validated placeholder requiring explicit SQLite and an explicitly available external provider; production remains invalid for every current backend/provider combination.

Phase 2 provides a frozen internal composition result over explicitly selected in-memory or SQLite Document State, one shared lifecycle service, all four lifecycle-aware writer services, and the Document State Query Facade adapter. Configuration validates before construction, unsupported modes fail closed, SQLite never falls back to memory, snapshot time is explicit, and safe summaries redact paths. API/auth/app and Streamlit activation, resource-bearing production shutdown, PostgreSQL/Supabase, and external identity providers remain deferred.

Phase 3 activates runtime composition in the API-owned app factory. `RuntimeConfig` and precomposed runtime entrypoints install an app-scoped facade provider, auth composition, safe diagnostics, and cleanup hook. Disabled and local-demo auth map to existing behavior; authenticated/production placeholders reject before construction. Default app behavior and all GET contracts remain compatible. Streamlit activation, real external identity, production persistence, and public mutations remain deferred.

Phase 4 adds a pure Streamlit-local preview contract with fixed runtime/backend/auth labels and bounded safe API runtime states. The controls are explicitly non-authoritative, do not import or construct platform services, and preserve API URL and allowlisted local-demo identity behavior. API unavailability, runtime/auth configuration failures, unauthorized/forbidden/concealed reads, and malformed envelopes use fixed messages without reflected backend details. Enforced deployment-mode selection, real production diagnostics, identity providers, and runtime activation remain outside Streamlit and deferred.

Phase 5 proves fail-closed behavior across validation, composition, API activation, auth mapping, Streamlit, imports, and privacy. Runtime bundles enforce backend/service invariants; caller-supplied compositions revalidate embedded config; unexpected construction errors are safely remapped; invalid app creation cannot reach FastAPI or compatibility providers; and recursive tests constrain all outer-layer imports. These guarantees do not make production available: PostgreSQL/Supabase, real identity, secrets, deployment operations, and production telemetry remain deferred.

Phase 6 confirms 84 Platform Runtime tests, 80 API tests with 9 skips, 64 Streamlit tests, 60 security tests, 330 Document State tests, 239 Query Facade/Review tests, and 1,535 full-regression tests with 9 skips. Boundary verification remains compliant. Closure documentation preserves the distinction between a verified fail-closed composition foundation and an unavailable production deployment.

References:

- `docs/architecture/PRODUCTION_COMPOSITION_RUNTIME_SELECTION_V1_PLAN.md`
- `docs/architecture/PRODUCTION_COMPOSITION_RUNTIME_SELECTION_V1_IMPLEMENTATION_PLAN.md`
- `docs/architecture/PRODUCTION_COMPOSITION_RUNTIME_SELECTION_V1_SUMMARY.md`
- `docs/architecture/PRODUCTION_COMPOSITION_RUNTIME_SELECTION_V1_HANDOFF.md`
- `docs/adr/ADR-021-production-composition-runtime-selection.md`
- `docs/releases/v0.16-production-composition-runtime-selection.md`

---

## FlowSync Document Intelligence UI v1

### Current Status

**v0.17 is implemented, verified, closed, and tagged as `v0.17-flowsync-document-intelligence-ui`.**

The approved product direction is a clean enterprise FlowSync application with sidebar navigation, safe tenant/user context, a document dashboard, detail/quality/review/workflow/audit views, and explicit unauthorized/unavailable states. It remains a separate API consumer and must not share domain state or business logic with FlowSync Competitor Price, root `dashboard.py`, legacy `src/api/app.py`, or Streamlit.

Current UI debt and prerequisites:

- The approved app exists at `apps/flowsync-document-intelligence/`; dependencies are installed and lockfile-controlled with zero current npm advisories. A real unit/component test runner, deployment, and package-maintenance ownership remain open.
- The current API is read-only and does not expose sanctioned raw document preview, raw correction values, upload, review decisions, reprocessing commands, workflow execution, or export actions.
- Real production identity/session and runtime adapters remain unavailable.
- A safe public workspace/user display contract may be needed before showing top-header context.
- Current processing/workflow/audit records may not support every desired lifecycle timeline correlation without an additive read contract.
- Final design system, responsive browser matrix, accessibility validation, deployment, CSP, telemetry, and analytics remain implementation work.

The v0.17 plan keeps API authorization and tenant scope authoritative, defines a GET-only envelope-validating client, treats unsupported mockup regions as explicit placeholders, and sequences implementation across six narrow phases. The approved mockup is a directional reference, not a pixel-perfect or backend-capability contract.

Phase 1 provides the isolated Vite/React/TypeScript boundary, responsive enterprise shell, approved route catalog, static safe page states, API-local public payload types, branded endpoint builders, GET-only client, strict v1 envelope validation, fixed non-reflective errors, and semantic theme foundations. It performs no live request at startup, installs no dependencies, and adds no auth/session, product data view, mutation, backend, Streamlit, dashboard, or competitor-price behavior.

Phase 2 provides API-backed document list/detail screens with bounded runtime payload projection, page-local cancellation-safe state, API-compatible filters, current-result search, stable status metrics and table columns, safe metadata, processing history, and validation/matching summaries. API failures remain visible with no fixture fallback. Review/workflow/audit correlations, raw preview, protected values, mutations, auth/session integration, dependency-backed typecheck/build, browser screenshots, and final theming remain deferred.

Phase 3 provides API-backed validation, matching, review queue/detail, workflow, and audit views with runtime payload parsers, bounded page-local state, safe correction summaries, dry-run reprocess summaries, confidence/severity/priority labels, and allowlisted audit display metadata. The pages add no commands, fixture fallback, API changes, or backend imports. Real auth/session integration, protected previews/values, server-backed correlation beyond existing identifiers, dependency-backed typecheck/build, browser/accessibility screenshots, and final theming remain deferred.

Phase 4 provides a normalized request-state catalog, fixed safe API/runtime/auth-configuration messages, concealed-resource handling, API-enforced access-scope notices, and non-authoritative runtime guidance. Frontend guards are usability-only: no identity/session adapter, login, role/permission decision, local scope security filter, credential storage, backend selection, or mutation was added. Real production identity integration, dependency-backed typecheck/build, browser/accessibility screenshots, and final product polish remain deferred.

Phase 5 provides a reproducible lockfile, advisory-free Vite 8 toolchain, passing dependency-free validation/strict typecheck/production build, and headless Chrome desktop/mobile/deep-link verification. The app starts safely without an API; shell spacing, responsive controls, unavailable states, runtime guidance, skip navigation, and menu semantics were verified. Comprehensive screen-reader/contrast automation, tablet matrix, live authenticated API smoke, unit/component test tooling, deployment, CSP, telemetry, and final visual theme remain deferred.

Phase 6 closes the read-only UI foundation with summary, handoff, release notes, final status records, and owner tag guidance. Remaining items are deferred product or production work rather than incomplete v0.17 scope: live authenticated API verification, identity/session integration, mutation and export contracts, protected preview/value access, deployment, full accessibility/browser automation, and final theming.

References:

- `docs/architecture/FLOWSYNC_DOCUMENT_INTELLIGENCE_UI_V1_PLAN.md`
- `docs/architecture/FLOWSYNC_DOCUMENT_INTELLIGENCE_UI_V1_IMPLEMENTATION_PLAN.md`
- `docs/adr/ADR-022-flowsync-document-intelligence-ui-boundary.md`
- `docs/architecture/FLOWSYNC_DOCUMENT_INTELLIGENCE_UI_V1_SUMMARY.md`
- `docs/architecture/FLOWSYNC_DOCUMENT_INTELLIGENCE_UI_V1_HANDOFF.md`
- `docs/releases/v0.17-flowsync-document-intelligence-ui.md`

---

## Export Runtime / ERP Integration Boundary v1

### Current Status

**v0.18 is implemented, verified, and closed pending owner tag.**

The platform now has a dependency-light export contract package, pure payload/idempotency policy, process-local attempt/result repositories, an injected internal service, safe history GET contracts, disabled mutation contracts, and a read-only FlowSync export placeholder. It still has no production readiness evaluator/source mapper, durable attempt/result persistence, real adapter, audit/lifecycle writer, reconciliation orchestration, or enabled public export command.

The v0.18 plan selects `src/export_runtime/` as a deterministic policy/orchestration boundary and keeps real vendor adapters, credentials, and network behavior outside core contracts. Readiness and `document:export` tenant authorization precede payload construction; attempts are claimed idempotently before delivery; only recorded confirmed success may request lifecycle advancement to `exported`.

Debt intentionally retained during planning:

- Export readiness evaluation, source projection mapping, durable repositories, real adapters, and platform composition
- Durable attempt/result schema and migration decision
- Real ERP/vendor adapters, SDKs, credentials, secret resolution, and network policy
- Unknown-delivery reconciliation, queue/worker, and transactional outbox
- Public authenticated export mutation routes and export-history reads
- Export-specific read permission decision
- FlowSync readiness/history presentation and future export controls
- CSV encryption, signing, delivery, retention, and download authorization
- Production telemetry, alerts, rate limits, SLOs, and operational runbooks

Phase 5 adds safe tenant-filtered export summaries and fixed disabled POST envelopes without composing or invoking the runtime. FlowSync remains GET-only and displays a disabled action. Phase 6 confirms 133 Export Runtime tests, 87 API tests with 9 skips, 84 Platform Runtime tests, 60 Security tests, 330 Document State tests, 239 Query Facade/Review tests, 64 Streamlit tests, and 1,675 full-regression tests with 9 skips. FlowSync validation/typecheck/build pass and boundary verification is compliant.

Phase 2 verification: 73 Export Runtime tests, 80 API tests with 9 skips, 84 Platform Runtime tests, 60 Security tests, 330 Document State tests, 239 Query Facade/Review tests, and 64 Streamlit UI tests pass. The full regression passes 1,608 tests with 9 skips. Runtime boundary verification is compliant with the two pre-existing U+FEFF warnings.

Phase 3 provides separate read/write repository Protocols, fixed repository errors, bounded stable attempt/result pages, atomic process-local uniqueness for attempt IDs and idempotency keys, expected-version attempt status transitions, one immutable terminal result per attempt, strict active duplicate lookup by idempotency key, and an optional same document-target active lock helper. State is process-local and non-durable; SQLite/Document State integration, retry/reconciliation orchestration, service composition, and API/UI reads remain deferred. Phase 3 focused verification passes 110 tests; all required API, Platform Runtime, Security, Document State, Query Facade/Review, and Streamlit UI suites pass unchanged. The full regression passes 1,645 tests with 9 skips.

Phase 4 provides synchronous internal orchestration over caller-owned readiness and identity facts. It uses injected repositories and one injected adapter, records terminal results before returning lifecycle intent, converts adapter exceptions to fixed safe failures, and returns bounded audit intents without writing them. Exact-key duplicates and active document-target conflicts are blocked before delivery; duplicate results are transient and do not overwrite stored history. Failed/unavailable outcomes intentionally recommend no lifecycle change. Durable attempts/results, async execution, retries/reconciliation, audit/lifecycle writers, real adapters, platform composition, API mutations, and UI actions remain deferred. Phase 4 focused verification passes 133 tests; all required compatibility suites pass unchanged. The full regression passes 1,668 tests with 9 skips.

Guardrails:

- UI/API routes must never call an ERP or repository directly.
- Export core must not own credentials, vendor SDKs, HTTP routing, or UI logic.
- Failed/unknown exports must not mark a document exported.
- Duplicate prevention must be atomic and tenant-scoped.
- No raw document/row/correction/artifact payload, credential, claim, path, stack trace, or vendor body may enter public records or audit.

References:

- `docs/architecture/EXPORT_RUNTIME_ERP_INTEGRATION_BOUNDARY_V1_PLAN.md`
- `docs/architecture/EXPORT_RUNTIME_ERP_INTEGRATION_BOUNDARY_V1_IMPLEMENTATION_PLAN.md`
- `docs/adr/ADR-023-export-runtime-erp-integration-boundary.md`

---

- Missing internal test data files required by `test_pipeline.py`:
  - `data/internal/supplier_prices.csv` (expected by `supplier_price_list` source)
  - `data/internal/erp_export.xlsx` (expected by `erp_inventory` source)
  - Recommendation: add small fixture CSV/XLSX files under `data/internal/` with representative rows (columns: `product_name`, `price`, `source`, `supplier_price` where applicable) or mock the file loader in tests.

- Connectors returning empty DataFrames during test runs:
  - `jumia_electronics` connector returned an empty DataFrame in CI environment.
  - Recommendation: implement connector mocks for tests or include deterministic local HTML fixtures/playwright profiles under `playwright_profiles/` to ensure reproducible extraction.

- Test expectations referencing `supplier_price` column:
  - Some pipeline/test code expects `supplier_price` column present after combining internal/external sources. If canonical pipeline does not produce `supplier_price`, update tests or mapping to use `price` with a `source` qualifier.

- Action items:
  1. Add minimal internal fixtures to `data/internal/` for CI.
  2. Add connector mocks or deterministic playwright fixtures under `playwright_profiles/`.
  3. Update `tests/test_pipeline.py` to mock external dependencies rather than relying on local network or missing files.

These items should be prioritized to make pipeline tests hermetic in CI environments.

---

## Workflow Runtime Locking v1 (CLOSED)

### Current Status

**Resolved in v0.5-workflow-runtime-locking milestone.**

The Workflow Runtime now has a complete locking subsystem that prevents duplicate concurrent execution of the same workflow. The solution includes three lock providers (database-backed with execution leases, file-based advisory locking, and in-memory for development), a pluggable provider registry with fallback chain, idempotency key deduplication for scheduled runs, and lease-based crash recovery.

### Resolution

- **Locking Infrastructure**: `src/workflow_runtime/locking/` package with 13 source files
- **Database Schema**: `scripts/migrations/006_create_workflow_locks_table.sql` and `007_create_workflow_idempotency_table.sql`
- **Configuration**: 13 constants in `src/workflow_runtime/locking/config.py` with documented defaults
- **Test Coverage**: 158 locking-specific tests (all passing) + full regression suite (363/364 passing)
- **Architecture Decision**: ADR-008-workflow-runtime-locking.md
- **Implementation Plan**: `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_PLAN.md`

### Effort

~13.5 person-days across 5 phases: Foundation → Infrastructure → Integration → Verification → Documentation & Release

### Reference

- `docs/architecture/WORKFLOW_RUNTIME_LOCKING_V1_SUMMARY.md`
- `docs/adr/ADR-008-workflow-runtime-locking.md`

---

## Contract Registry v1 Follow-Up

### Current Status

Contract Registry v1 is formally closed with repository-owned JSON Schema Draft 07 contracts, example fixtures, local validation tests, and `scripts/validate_contracts.py`. CI Contract Validation v1 now runs the contract pytest suite and standalone validator in GitHub Actions with a minimal dependency install.

### Remaining Debt

- Schema compatibility checks against a released baseline are not yet implemented.
- ADR enforcement for breaking schema changes is not yet implemented.
- Schema version bump validation is not yet implemented.
- Runtime boundary validation is not yet implemented.
- Runtime producers and consumers do not yet perform mandatory contract validation.

### Recommended Solution

1. Confirm GitHub Actions runs the new contract-validation workflow successfully.
2. Add compatibility diffing for schema changes in a later hardening phase.
3. Require ADR validation for MAJOR schema version changes in a later hardening phase.
4. Implement Runtime Boundary Verification as the next v0.5 hardening objective.

### Priority

Medium (remaining v0.5 Runtime Hardening follow-up).

---

## Entity Runtime Concurrency Hardening (CLOSED)

### Current Status

**Resolved in the v0.5-entity-runtime-concurrency-hardening milestone.**

The Entity Runtime now supports versioned persistence, optimistic locking, pessimistic lock escalation, execution leases, and idempotency protection for entity writes. The implementation includes runtime integration, graceful degradation, and regression coverage for unit, integration, crash-recovery, and verification scenarios.

### Resolution

- Versioned entity persistence and history via `src/entity_runtime/store/`
- Concurrency orchestration via `src/entity_runtime/concurrency/guard.py`
- Runtime integration via `src/entity_runtime/orchestration/orchestrator.py`
- Regression and verification coverage under `tests/entity_runtime/`
- Architecture and handoff documentation under `docs/architecture/` and `docs/adr/`

### Reference

- `docs/architecture/ENTITY_RUNTIME_CONCURRENCY_HARDENING_V1_SUMMARY.md`
- `docs/architecture/ENTITY_RUNTIME_CONCURRENCY_HARDENING_V1_HANDOFF.md`
- `docs/adr/ADR-010-entity-runtime-concurrency-hardening.md`

---

## Scheduler State Separation

### Current Issue

`src/schedules.json` mixes two concerns:
1. **Configuration** (version-controlled): workflow schedule definitions (`frequency`, `time_of_day`, `enabled`)
2. **Runtime State** (ephemeral): execution history (`last_run`, `next_run`, `run_count`)

This causes:
- Frequent, spurious diffs when tests or manual runs update runtime state
- Accidental commits of environment-specific execution history
- Difficulty distinguishing intentional configuration changes from automated state updates

### Root Cause

Scheduler loads and mutates all fields in a single JSON file during runtime, so all updates get reflected in source control when the file is committed.

### Recommended Solution (v0.5+)

Separate configuration from state:

#### Option A: Two Files (Recommended for simplicity)
- **`src/schedules.config.json`** (version-controlled): Configuration only
  ```json
  {
    "electronics_monitoring": {
      "workflow_id": "...",
      "frequency": "daily",
      "time_of_day": "08:00",
      "enabled": true
    }
  }
  ```
- **`src/schedules.state.json`** (auto-generated, add to `.gitignore`): Runtime state only
  ```json
  {
    "electronics_monitoring": {
      "last_run": "2026-05-27T08:00:23.039256",
      "next_run": "2026-05-28T08:00:00",
      "run_count": 5
    }
  }
  ```

#### Option B: Database-Backed State
- Keep `src/schedules.config.json` (version-controlled, config only)
- Store execution history in SQLite (`src/execution_history.db` or shared scheduler DB)
- Add `.db` files to `.gitignore`

#### Option C: Schema Separation (Single File)
```json
{
  "configurations": { /* version-controlled */ },
  "runtime_state": { /* ephemeral, handle separately */ }
}
```

### Implementation Steps

1. Create `src/schedules.config.json` with configuration-only content
2. Update `src/scheduler.py` to load config from `.config.json` and state from `.state.json` (or DB)
3. Add to `.gitignore`:
   ```
   src/schedules.state.json
   src/execution_history.db
   ```
4. Update CI/CD to initialize fresh state files on each run
5. Update developer onboarding docs

### Effort

Low — ~4 hours refactor; minimal impact on scheduler logic

### Priority

Medium (v0.5 or later); does not block v0.4 release
