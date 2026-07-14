# Export Runtime / ERP Integration Boundary v1 Plan

**Milestone:** v0.18
**Status:** Phases 1-3 implemented and verified; Phase 4 not started
**Recommended package:** `src/export_runtime/`

## 1. Problem Statement

The platform can ingest, process, validate, match, review, persist, and present document lifecycle state, including the existing `approved`, `export_ready`, and `exported` document statuses. It does not yet have a governed boundary that decides whether a document may be exported, builds a sanitized target payload, prevents duplicate delivery, records attempts/results, invokes an isolated adapter, audits the operation, and advances lifecycle state only after confirmed success.

Adding an ERP call directly to the API, UI, workflow writer, or Document State repository would bypass readiness, authorization, tenant scope, idempotency, audit, and lifecycle rules. v0.18 therefore establishes the export runtime before any real ERP integration or public export mutation is activated.

## 2. Current State

- `Permission.DOCUMENT_EXPORT` (`document:export`) already exists.
- Tenant-aware default-deny authorization, explicit service-account scope, and cross-tenant controls already exist under `src/security/`.
- `DocumentStatus` already includes `approved`, `export_ready`, and terminal `exported`.
- `LifecycleAdvancementService` governs projection updates and optimistic conflicts.
- Document State provides repository, writer, audit, idempotency, and in-memory/SQLite foundations.
- Platform Runtime owns explicit composition; API and FlowSync do not construct runtime services.
- The Document Intelligence API and FlowSync UI are read-only. No export endpoint or action exists.

## 3. Goals

1. Define a deterministic, runtime-neutral export domain boundary.
2. Separate export policy/orchestration from ERP and file delivery adapters.
3. Require readiness, authorization, and tenant checks before payload construction or delivery.
4. Define immutable JSON-compatible payload, attempt, result, audit, and lifecycle contracts.
5. Prevent duplicate exports through stable idempotency and atomic attempt claims.
6. Keep adapter credentials and transport details outside core contracts.
7. Record every accepted export operation and terminal outcome safely.
8. Advance a document to `exported` only after confirmed adapter success.
9. Preserve API authority and make future FlowSync controls consumers only.
10. Support deterministic placeholder and CSV/file adapters without a real ERP dependency.

## 4. Non-Goals

- Creating `src/export_runtime/`, tests, endpoints, UI controls, migrations, or dependencies during planning.
- Connecting SAP, Oracle, Dynamics, NetSuite, Supabase, or any external system.
- Implementing production credentials, secret resolution, network retries, queues, or workers.
- Uploading raw documents or rows to an adapter.
- Adding public mutation routes before export contracts, authorization, persistence, and audit are verified.
- Changing existing API payloads, FlowSync behavior, Streamlit, `dashboard.py`, or competitor-price modules.
- Treating CSV generation as proof of production ERP readiness.

## 5. Export Product Boundary

Recommended architecture:

```text
Future FlowSync export control
  -> authenticated Document Intelligence API command boundary
  -> ExportRuntimeService
  -> readiness + permission + tenant policy
  -> payload builder
  -> idempotency / attempt repository
  -> ExportAdapterPort
  -> structured ExportResult
  -> audit + lifecycle advancement
```

The export runtime owns readiness, safe payload construction, attempt orchestration, idempotency, result interpretation, audit intent, and lifecycle decision. It does not own HTTP routing, browser state, credentials, vendor SDKs, database engines, or document processing.

## 6. Export Runtime Versus ERP Adapters

The **export runtime** is deterministic domain logic. It validates an authorized request, reads approved projections, builds a target-neutral or target-versioned payload, claims an idempotency key, records an attempt, invokes one injected adapter, records the result, emits audit intent, and requests lifecycle advancement.

An **ERP adapter** is an integration implementation behind `ExportAdapterPort`. It converts an already sanitized payload into a vendor request and returns a bounded structured result. It may not decide readiness, permissions, tenant scope, document status, retries, or lifecycle. Credentials are injected by the outer composition boundary and never enter payloads, results, logs, or audit metadata.

Real vendor adapters should live in explicit integration packages such as `src/integrations/erp/<vendor>/`, while safe placeholder adapters may live under `src/export_runtime/adapters/` for contract tests. This prevents the core package from accumulating vendor dependencies.

## 7. Recommended Package Design

```text
src/export_runtime/
  __init__.py
  contracts.py
  payloads.py
  readiness.py
  attempts.py
  results.py
  idempotency.py
  errors.py
  ports.py
  service.py
  adapters/
    __init__.py
    csv_placeholder.py
    erp_placeholder.py
```

`src/export_runtime/` is preferred over a Workflow Runtime or API subpackage because export has its own policy, idempotency, persistence, and integration lifecycle. It must consume narrow public ports and remain independent of HTTP and UI code. Platform Runtime should compose concrete security, repository, lifecycle, audit, and adapter implementations later.

## 8. Core Contracts

All contracts should be immutable, versioned where payload compatibility matters, deterministic, and JSON-compatible.

- `ExportTarget`: target ID, adapter type, safe display label, payload schema/version, and enabled capability; never credentials or connection strings.
- `ExportPayload`: payload ID/version, document/tenant opaque IDs, target ID, document projection version, safe business fields, canonical metadata, and payload fingerprint.
- `ExportReadinessResult`: ready flag, ordered check results, safe reason codes, document version, and target ID.
- `ExportAttempt`: stable attempt ID, document/tenant/target IDs, idempotency key digest, payload fingerprint, status, actor reference, timestamps, retry lineage, and safe metadata.
- `ExportResult`: attempt ID, terminal success/failure classification, safe adapter code, optional bounded external reference, timestamps, and retryability; no raw adapter body.
- `ExportStatus`: fixed operation-state catalog kept separate from document lifecycle status.
- `ExportIdempotencyKey`: bounded digest derived from approved canonical inputs.
- `ExportAuditIntent`: event type, document/attempt/target references, actor reference, outcome code, timestamp, and bounded scalar metadata.
- `ExportPermission`: required permission and evaluated tenant/resource scope; authorization decisions remain owned by `src/security/`.
- `ExportLifecycleDecision`: whether success permits advancement, expected document version, lifecycle result, and projection-pending state.

## 9. Export Status Model

Export operation status is separate from `DocumentStatus`:

- `not_ready`: readiness checks failed; no adapter call.
- `ready`: checks passed; payload may be prepared.
- `preparing`: payload construction or persistence is in progress.
- `queued`: accepted for later delivery when an execution model exists.
- `exporting`: one claimed attempt is invoking its adapter.
- `exported`: adapter confirmed success and the result is recorded.
- `failed`: terminal attempt failure; document is not falsely exported.
- `cancelled`: cancelled before external confirmation under a future governed command.
- `duplicate_prevented`: an equivalent active/successful attempt already owns the idempotency key.

`queued` and `cancelled` remain reserved until asynchronous execution and cancellation contracts exist. They must not be simulated by a synchronous placeholder.

Document lifecycle remains governed by existing `DocumentStatus`. An export attempt does not add transient export statuses to `DocumentRecord`. Only confirmed success may request `export_ready -> exported` or another explicitly approved existing transition.

## 10. Export Readiness Policy

Readiness is a pure, ordered policy evaluated after identity and tenant authorization and before payload building. Required checks are:

1. document exists within the authorized tenant scope;
2. caller has `document:export` for that resource;
3. lifecycle status is `approved` or `export_ready` according to target policy;
4. validation has passed or has no blocking error;
5. matching is complete when required for the document type/target;
6. required review is approved;
7. required entity/reference summaries are present;
8. target is configured and enabled by explicit composition;
9. no active or successful equivalent export owns the idempotency key;
10. the sanitized payload can be built and validated.

Checks return stable codes and safe field names, not raw values. `approved` may pass business readiness but should normally advance to `export_ready` before delivery. Direct `approved -> exported` is already possible in the lifecycle catalog, but v0.18 should prefer explicit `export_ready` unless a target policy documents why the shortcut is valid.

## 11. Payload Model

The payload builder is pure and must not call adapters or mutate repositories. It receives only approved projections and target schema configuration. It produces canonical field ordering, explicit schema version, deterministic scalar/list/object types, and a payload fingerprint.

Payload contracts exclude raw document bytes, raw rows, protected correction values, unrestricted metadata, credentials, tokens, claims, storage paths, backend references, and raw exceptions. Target-specific mapping belongs in a versioned mapper, not in API routes or UI components.

## 12. Attempt And Result Records

An attempt represents one claimed delivery operation. A result represents the adapter-confirmed outcome for that attempt. Attempts should be append-oriented; status advancement uses optimistic versioning or a narrowly defined compare-and-swap transition. Results are immutable and append-only.

The runtime should persist the accepted attempt before external delivery, then persist a terminal result after the adapter returns. If result persistence is uncertain after an external success, the attempt becomes reconciliation-required and must never be blindly resent. The safe API/UI projection should expose status and reason codes only.

## 13. Idempotency And Duplicate Prevention

The canonical idempotency digest includes domain separation plus tenant ID, document ID, target ID, payload fingerprint, operation type, and operation version. The payload fingerprint already covers payload schema and document projection version. Caller-supplied request keys may be included later as an additional bounded input but cannot replace the server-derived digest.

The attempt repository must enforce a unique claim atomically. Concurrent requests with the same digest cannot both invoke the adapter. Replays return the existing attempt/result or `duplicate_prevented`. A retry after a retryable failure creates a new attempt linked to the prior attempt and uses an explicit retry ordinal or retry command while preserving the original operation lineage.

## 14. Audit Trail

Audit events should cover readiness denied, payload prepared, attempt claimed, duplicate prevented, adapter started, export succeeded, export failed, retry requested, lifecycle advanced, and lifecycle projection pending. Audit append uses deterministic idempotency keys.

Audit metadata is bounded and allowlisted: target ID, status/reason code, attempt count, retry ordinal, and safe external-reference presence. Payloads, credentials, claims, adapter bodies, paths, and exception text are forbidden.

## 15. Lifecycle Behavior

- Readiness failure does not change document lifecycle.
- Payload preparation does not mark the document exported.
- Adapter failure records a failed export result and audit event; the document remains `approved` or `export_ready`.
- Adapter success is recorded before lifecycle advancement is requested.
- Confirmed success may advance the document to `exported` through `LifecycleAdvancementService` with the expected document version.
- If lifecycle advancement conflicts after recorded success, return `projection_pending`; repair the projection without invoking the adapter again.
- `exported` remains terminal. Repeat equivalent requests return the recorded success or `duplicate_prevented`.

Cross-store atomicity is not assumed. The implementation must use durable attempt/result state plus replay-safe audit and lifecycle repair, or a future transactional outbox when production persistence requires it.

## 16. Permission And Tenant Model

- Every export preparation or execution command requires authenticated mode and `document:export`.
- The security guard resolves the document tenant before readiness or payload construction.
- Tenant scope must match the document, attempt, target assignment, and audit record.
- Service accounts require explicit tenant scope and explicit `document:export`; the `service_account` role grants no permission by itself.
- `platform_admin` does not gain implicit cross-tenant export. Cross-tenant operation requires explicit enablement, active target tenant, and auditable authorization.
- Export history reads require `audit:read` initially or a separately approved `export:read` permission.
- Disabled/local unauthenticated API modes may support deterministic internal tests but must not activate real export mutations.

## 17. Future API Mutation Boundary

Potential routes, not implemented by this planning phase:

- `POST /api/v1/documents/{document_id}/export/prepare`
- `POST /api/v1/documents/{document_id}/export`
- `GET /api/v1/documents/{document_id}/exports`
- `GET /api/v1/export-attempts`
- `GET /api/v1/export-attempts/{attempt_id}`

The POST boundary must use authenticated-only composition, `document:export`, tenant/resource guards, a required bounded idempotency key, strict request contracts, safe `409` duplicate/conflict behavior, and standard envelopes/request IDs/security headers. `prepare` performs no external call. `export` never accepts credentials, raw payloads, arbitrary target URLs, or tenant overrides.

No route should be activated until Phases 1-4 verify runtime, persistence, adapter, audit, and lifecycle behavior. Whether POST activation belongs in v0.18 Phase 5 or a dedicated v0.19 mutation milestone is an owner release gate.

## 18. Future FlowSync Impact

FlowSync may later display an export readiness panel, status badge, attempt history, safe failure explanation, and target/adapter display labels. Export controls remain disabled until an authenticated mutation API is approved and integrated. The UI never computes readiness, grants permission, selects tenant scope, submits credentials, constructs payloads, or calls an ERP directly.

## 19. Adapter Strategy

`ExportAdapterPort` should expose a narrow operation such as `export(payload, context) -> ExportResult`. Adapter context contains safe attempt/target references and resolved non-serializable credential handles supplied by composition, never secrets in contracts.

- `csv_placeholder`: deterministic local/dev serializer for contract and mapping verification. It returns bytes or an opaque artifact reference through a safe sink port; it does not leak filesystem paths.
- `erp_placeholder`: deterministic unavailable/success fixture selected explicitly in tests; no network or vendor SDK.
- Real ERP adapters: separate packages, explicit dependency ownership, timeout/retry/circuit policy, secret resolver, contract tests, and deployment review.

Core contracts make no external call and import no vendor dependency.

## 20. Failure, Retry, And Reprocess

Failures use stable classes: `not_ready`, `permission_denied`, `tenant_denied`, `invalid_payload`, `duplicate`, `adapter_unavailable`, `adapter_rejected`, `timeout_unknown`, `result_persistence_failed`, `lifecycle_conflict`, and `internal_error`.

Retryability is explicit in the result. Known pre-delivery failures may retry under policy. Unknown delivery outcomes require reconciliation, not automatic resend. Document reprocessing is separate from export retry: reprocess may produce a new document version and therefore a new idempotency digest. Export failure must never silently mark processing failed or exported.

## 21. Persistence And Composition

Export core defines read/write ports for attempts and results. A later persistence adapter may extend Document State records/repositories and SQLite schema behind those ports; API and UI never access repositories directly. Platform Runtime explicitly injects repositories, security guard, readiness sources, lifecycle service, audit writer, target catalog, adapter registry, and credential resolver. Unsupported or missing adapters fail closed with no fallback.

## 22. Privacy And Safety Rules

Contracts, persistence, logs, audit, API responses, and UI projections must exclude raw documents, raw rows, protected correction values, unrestricted artifact payloads, credentials, tokens, raw claims, storage/backend paths, DSNs, stack traces, raw exceptions, vendor request/response bodies, and unrestricted metadata. External references and adapter messages are bounded and sanitized before persistence.

## 23. Testing Strategy

- Contract immutability and JSON serialization.
- Readiness rule ordering and every denial reason.
- Payload schema validation, canonicalization, and privacy rejection.
- Deterministic idempotency and concurrent duplicate claims.
- Permission, service-account scope, tenant denial, and explicit cross-tenant behavior.
- Adapter success, rejection, unavailable, timeout-unknown, and sanitized error mapping.
- Attempt/result persistence, retries, reconciliation, and audit idempotency.
- Lifecycle advancement only after recorded confirmed success; projection repair without redelivery.
- In-memory/SQLite repository conformance if persistence is added.
- API guard/envelope/idempotency behavior before mutation activation.
- FlowSync disabled/future action behavior before mutation integration.
- Recursive boundary/import checks proving no UI/API/vendor dependency in core.

## 24. Proposed Phases

1. Export runtime contracts and status/readiness model.
2. Export payload builder and idempotency policy.
3. Export attempt/result repository integration.
4. Export service with placeholder adapters and lifecycle/audit integration.
5. API mutation contract boundary and FlowSync export-readiness placeholders, gated from activation until owner approval.
6. Verification, documentation, release closure, handoff, and tag recommendation.

Phase 1 delivers the standard-library-only `src/export_runtime/` contract package. It defines fixed export/attempt/readiness/target/operation catalogs; immutable target, permission, readiness, payload party/line, attempt, adapter result, export result, lifecycle decision, and audit intent contracts; bounded scalar metadata; deterministic canonical payload fingerprints and domain-separated idempotency keys; fixed privacy-safe errors; and a structural `ExportAdapterPort`. It implements no readiness evaluator, payload mapper, repository, service, adapter, API/UI integration, persistence, I/O, or external call. Thirty-eight focused tests and all required regressions pass.

Phase 2 adds a pure `ExportPayloadBuilder` over safe, already-structured command inputs; deterministic whitespace, currency, and date normalization; domain-separated canonical payload fingerprints; an explicit idempotency policy over the Phase 1 key foundation; and `payload_invalid` readiness linkage. Unsafe/raw-shaped inputs and unrestricted metadata fail with fixed non-reflective results. The builder performs no repository, facade, API, adapter, persistence, or I/O work. The combined Export Runtime suite passes 73 tests and all required regressions pass.

Phase 3 adds persistence-neutral read/write repository Protocols, bounded deterministic attempt/result queries, fixed repository-safe errors, and an explicitly composed lock-protected in-memory store. Attempts and idempotency keys are unique, attempt status updates use optimistic versions and a fixed transition catalog, terminal results are immutable and require an existing matching attempt, and safe list projections contain no payload body or adapter response. Strict duplicate identity is the idempotency key; a separate optional helper reports an active same-tenant/document/target operation. No SQLite, Document State, service, adapter, lifecycle mutation, API/UI integration, or I/O is added. The combined Export Runtime suite passes 110 tests and all required compatibility suites pass.

## 25. Deferred Work

- Real ERP/vendor adapters and SDKs.
- Production credentials, secret manager, network policy, queues, workers, and circuit breakers.
- Public mutation activation if not approved in v0.18 Phase 5.
- Production PostgreSQL/Supabase export persistence and transactional outbox.
- FlowSync export execution controls and protected payload/preview UI.
- ERP-specific field mapping, schema negotiation, acknowledgements, and reconciliation jobs.
- File retention, encryption, delivery, signing, and download policy.
- Production telemetry, alerting, SLOs, rate limiting, and operational dashboards.

## 26. Risks And Open Questions

- External success followed by local persistence failure creates an unknown-delivery state that requires reconciliation.
- Existing Document State transactions do not span an ERP call; outbox/reconciliation design may be required for production.
- The exact boundary between `approved` and `export_ready` needs owner policy by document type and target.
- Export payload fields and target schema ownership are not yet defined for a real ERP.
- `audit:read` may be too broad for export-history consumers; a future `export:read` permission may be safer.
- Cross-tenant platform-admin export should probably remain disabled unless a concrete support workflow proves necessary.
- CSV output ownership, encryption, retention, and download authorization require separate policy.

## 27. Acceptance Criteria

- Export runtime and adapter responsibilities are separate and explicit.
- Readiness, permission, tenant, payload, idempotency, attempt/result, audit, lifecycle, retry, and privacy contracts are defined.
- No UI or API can call an ERP directly or decide export authorization.
- Duplicate delivery is prevented atomically and safely replayed.
- Failed or uncertain attempts cannot falsely advance the document to `exported`.
- Only confirmed recorded success can request governed lifecycle advancement.
- Real ERP connections, dependencies, endpoints, migrations, and UI actions remain unimplemented during planning.
