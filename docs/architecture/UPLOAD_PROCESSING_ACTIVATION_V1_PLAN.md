# Upload + Processing Activation v1 Plan

**Milestone:** v0.19
**Status:** Implemented, verified, and closed pending owner tag
**Recommended package:** `src/upload_runtime/`

## 1. Goal

Define and phase a safe mutation boundary through which an authenticated, tenant-scoped user can upload one supported document and request deterministic ingestion/processing. The API remains authoritative for identity, tenant, permission, validation outcome, accepted document identity, processing state, and errors. FlowSync is a transport client and status viewer only.

## 2. Non-Goals

- No implementation, endpoint, UI behavior, migration, or dependency in planning.
- No production blob-storage selection, raw-file download, public artifact URL, or retention/legal-hold solution.
- No OCR, LLM, agent, real ERP, export activation, or automatic export.
- No client-side parsing, classification truth, processing result construction, permission decision, or lifecycle advancement.
- No forced async queue/outbox design unless required before production activation.
- No changes to Streamlit, `dashboard.py`, or competitor-price modules.

## 3. Planning Baseline And Delivered State

- `DocumentIngestionEngine` and `IngestionPipeline` deterministically load/classify/normalize/parse/validate path-based inputs.
- Existing loaders recognize PDF, CSV, XLS/XLSX, TXT, and EML.
- `src/document_state/writers/` already defines safe ingestion/processing commands, idempotency, record mapping, and repository-neutral writers.
- Lifecycle policy/service govern document snapshot advancement; Query Facade and API already project documents and processing history.
- `document:ingest` exists and is assigned only to approved roles/service accounts.
- API raw-file transport/storage and processing mutation composition are not active. FlowSync provides a guarded metadata preview and read-only progress UI.

The planning gap was a controlled raw-byte boundary between HTTP transport and the existing path-based ingestion producer, plus safe orchestration into Document State. v0.19 closes the contract, validation, intent, progress-read, API-preview, and FlowSync portions of that gap. Raw-file transport, real staging, ingestion execution, and concrete Document State adapters remain deferred.

## 4. Architecture Decision

Use a small standard-library-first `src/upload_runtime/` package rather than placing validation in FastAPI routes or Document State writers. Upload validation, safe metadata, upload identity/status, and ingestion activation commands form a reusable policy boundary. API code owns the current JSON metadata transport and authorization; any future multipart transport also belongs at that outer boundary. A future producer-side adapter will own controlled staging and call the existing ingestion pipeline. Existing Document State writers remain the persistence boundary.

```text
FlowSync upload preview
  -> Guarded upload metadata API
  -> Upload Runtime validation
  -> Opaque staging boundary
  -> Activation intents
  -> Ingestion / Document State adapter ports
  -> Progress projections
  -> FlowSync progress timeline
```

No raw bytes cross the v0.19 boundary. The current POST accepts JSON metadata only. Any future raw transport must terminate at an approved private staging adapter and must never embed bytes or paths in JSON commands, writer records, audit metadata, public responses, or UI state.

## 5. Proposed Package Boundary

Planning target:

```text
src/upload_runtime/
  __init__.py
  contracts.py
  validation.py
  commands.py
  results.py
  errors.py
  ports.py
  service.py          # only when orchestration begins
```

- `contracts.py`: immutable upload metadata, file descriptor, validation issue, status, and safe summary contracts.
- `validation.py`: pure filename/extension/size/empty/type-consistency/metadata policy.
- `commands.py`: accepted upload and processing-activation commands containing identities and an opaque artifact handle, never raw bytes/path.
- `results.py` / `errors.py`: fixed safe outcomes and non-reflective messages.
- `ports.py`: streaming/staging, ingestion producer, clock/ID, and optional upload-summary persistence ports.
- `service.py`: gated orchestration after contracts are proven.

`upload_runtime` must not import FastAPI, FlowSync, Streamlit, Document State implementations, SQLite, ERP/export runtime, vendor SDKs, or external services. Producer adapters outside the package map accepted commands to ingestion and writer commands.

## 6. Upload Product Boundary

An upload is one tenant-owned request with a stable `upload_id`, actor, safe filename, declared media type, detected/validated type, byte count, source label, timestamps, correlation/idempotency identity, and status. The public response returns identifiers and safe status only. It never returns bytes, content excerpts, local paths, raw headers, claims, or storage configuration.

The server assigns `upload_id` and `document_id`. Client-supplied document type is a hint only; the ingestion classifier remains authoritative. Conflicts between declared type, extension, signature, and detected type fail safely or route to review under an explicit future policy.

## 7. Supported File Types

Initial allowlist candidates are PDF, CSV, XLSX, TXT, and EML because loaders already exist. Legacy XLS is recognized internally but should remain deferred until security, parser, and fixture coverage justify activation. No archive, executable, script, macro-enabled Office, image-only, HTML, or arbitrary binary type is accepted.

Type activation is per-format and requires fixtures, parser/loader conformance, size/resource limits, signature/MIME policy, privacy checks, and deterministic failure mapping. OCR-dependent scanned PDFs remain accepted only if the existing deterministic loader can produce usable content; OCR is explicitly deferred.

## 8. File Safety Validation

Validation happens before staging/ingestion and uses fixed ordering:

1. Request and permission/tenant gate.
2. Bounded filename presence and normalization.
3. Reject absolute paths, separators, traversal, control characters, reserved names, multiple unsafe suffixes, and executable/script extensions.
4. Reject empty content and enforce per-file and request size limits while streaming.
5. Extension allowlist.
6. Declared media type allowlist and extension consistency.
7. Practical signature/magic checks for PDF/XLSX; text/CSV/EML receive bounded text/structure checks.
8. Bounded safe metadata and source/actor attribution.
9. Compute content digest for idempotency without returning it publicly unless approved.

Fixed failure codes: `unsupported_file_type`, `upload_too_large`, `upload_empty`, `unsafe_filename`, `type_mismatch`, `metadata_invalid`, `permission_denied`, `tenant_denied`, `mutation_not_enabled`, `ingestion_failed`, `parsing_failed`, `extraction_failed`, `validation_failed`, `matching_failed`, and `internal_error`.

Malware scanning is a production prerequisite but no new scanner dependency is selected in this milestone plan.

## 9. Upload Metadata Contract

Allow only bounded scalar fields: source label/type, client correlation ID, client request ID, optional batch ID, declared media type, and optional document-type hint. Server-derived tenant, actor, sizes, timestamps, IDs, and validated type cannot be overridden. Reject nested values and keys suggesting content, paths, credentials, claims, tokens, backend configuration, or unrestricted metadata.

## 10. Ingestion Command Contract

The upload service produces an immutable command containing `upload_id`, `document_id`, tenant/actor identities, safe filename, validated format, opaque staged-artifact reference, content digest/idempotency identity, received timestamp, and bounded source metadata. The opaque reference is resolved only by the ingestion adapter. Writer commands receive safe projections from ingestion results, not serialized producer results.

## 11. Processing Activation Model

Initial implementation should be synchronous/local-demo or explicitly queued behind a port; production activation fails closed until resource, timeout, durability, and recovery policies exist. The accepted upload is recorded before processing starts. Each stage reports a safe processing snapshot and lifecycle intent. Partial completion is retained and replay uses stable source event IDs.

Planned stages:

`received -> upload_validated -> ingestion_started -> ingested -> parsed -> extracted -> transformed -> validated -> matched -> review_required`

`approved` and `export_ready` remain later governed outcomes. Upload never triggers export. Stages unsupported by the current deterministic pipeline must not be fabricated; they remain pending/deferred or are added only with an actual producer and mapping.

## 12. Document State Writer Integration

Reuse `IngestionDocumentStateWriter`, `ProcessingDocumentStateWriter`, their command contracts, idempotency rules, and injected repository ports. A producer-side adapter maps safe ingestion outcomes to `CreateDocumentCommand`, lifecycle events, processing snapshots, validation issues, and matching summaries. Do not pass raw ingestion/parsing objects to writers.

The first durable record should establish tenant-owned document status `received`. Governed lifecycle advancement then applies `received -> ingested` and later supported transitions with expected versions. Cross-record writes use deterministic checkpoint order and resumable idempotency; v0.19 must not claim distributed exactly-once behavior.

## 13. Lifecycle Behavior

- Validation acceptance does not equal ingestion success.
- Create the document and received event before processing advancement.
- Advance only after the corresponding safe producer result is recorded.
- Failures never skip forward or mark review/approval/export states.
- Terminal processing failure records a safe failed snapshot/audit outcome; whether document lifecycle becomes `failed` must follow existing policy and expected-version checks.
- Retry/replay preserves upload/document/source identities and never duplicates successful stages.
- No upload path may request `exported` or invoke Export Runtime.

## 14. API Boundary

Routes delivered through Phases 2 and 4:

- `POST /api/v1/documents/upload`
- `GET /api/v1/uploads`
- `GET /api/v1/uploads/{upload_id}`
- `GET /api/v1/uploads/{upload_id}/progress`
- `GET /api/v1/uploads/{upload_id}/timeline`
- `GET /api/v1/documents/{document_id}/processing-status`

The POST route accepts strict JSON metadata only; multipart and raw bytes are not implemented. It remains staging-disabled. The API authorizes `document:ingest` where authentication is enabled, enforces active tenant scope, binds actor attribution, applies metadata policy, and returns the standard envelope. Valid authorized metadata reaches the governed staging-disabled state rather than claiming upload success. GET history/status reads are tenant-scoped and conceal unauthorized resources.

Default/unauthenticated mode must not mutate. Production/unsupported composition fails closed. Error responses contain fixed codes/messages and safe field names only.

## 15. Tenant And Security Rules

- Require authenticated principal, active tenant, and `document:ingest` for mutation.
- Never accept tenant or actor identity from client metadata or any future multipart fields.
- Service accounts require explicit tenant scope and permission; cross-tenant upload is disabled.
- Authorize before buffering/staging significant content where transport permits.
- Bind upload, artifact handle, document, audit, and processing identities to the same tenant.
- Upload history and processing reads apply tenant narrowing before lookup/projection.
- Use idempotency/request identity to prevent accidental duplicate ingestion.
- Raw download remains deferred.

## 16. FlowSync UI Delivery

Phase 5 preserves the v0.17 dark-green sidebar, white workspace, calm enterprise layout, green semantic status accents, and API-authority language. `/uploads` provides an accessible browser-local picker, selected filename/type/size, safe validation feedback, recent tenant-scoped uploads, API-supplied processing timelines, and manual refresh while staging remains disabled.

The UI sends only filename, size, inferred extension, and browser content type after the explicit **Validate upload** action. It does not inspect content, determine final document type, generate IDs, decide access, expose paths, trigger export, or fabricate processing events. Approximate progress is labeled only when supplied by the API.

## 17. Privacy And Audit

Never expose or persist raw files in API JSON, raw rows/text, parser output, extracted entities, credentials, tokens, claims, backend/staging paths, stack traces, raw exceptions, multipart headers, or unrestricted metadata. Audit safe events such as upload requested/accepted/rejected, ingestion started/completed/failed, and processing stage changes using stable IDs, tenant/actor attribution, format, byte-count bucket if approved, fixed outcomes, and timestamps—not filenames when avoidable and never content.

## 18. Test Strategy

Plan focused tests for valid commands; each supported type; unsupported, empty, unsafe-name, oversized, mismatched-type, executable, traversal, and metadata rejection; tenant and permission denial; disabled mutation; service-account scope; idempotent retries; ingestion command mapping; received/ingested lifecycle; processing projections; partial failure/replay; safe errors/audit; no raw bytes/path leakage; no export trigger; no ERP/external dependency; FlowSync disabled/ready states; no client-side classification/permission; and recursive import boundaries. Retain all API, security, Document State, lifecycle, Query Facade, FlowSync, Streamlit, export, and full regressions.

## 19. Deferred Work

Production blob storage, malware scanning vendor, raw download, retention/legal hold, PostgreSQL/object storage, queue/outbox/workers, distributed recovery, OCR/LLM, image uploads, legacy XLS, archive formats, batch upload, resumable/chunked upload, antivirus quarantine UI, production rate limiting/gateway controls, enabled export, ERP, and upload-to-export automation.

## 20. Risks And Open Questions

- Current ingestion accepts file paths and may emit raw-rich results; staging and projection adapters require strict ownership.
- Synchronous processing can exceed HTTP timeouts and needs a queue decision for production.
- Production storage, malware scanning, retention, deletion, and legal hold are undecided.
- MIME/signature verification without a dependency has limits.
- XLSX decompression/resource bombs require bounded parsing policy.
- EML may contain attachments and sensitive headers requiring a narrower policy.
- Current lifecycle stage vocabulary does not automatically prove all proposed stages.
- Partial writer success requires deterministic replay and operational visibility.
- A separate `document:upload` permission may be clearer than reusing `document:ingest`.
- Upload idempotency semantics across identical content, filenames, and intentional re-upload need owner policy.

## 21. Acceptance Criteria

- Contracts and validation are deterministic, immutable, bounded, and privacy-safe.
- API authorization/tenant validation occurs before mutation and significant staging.
- Only approved types and sizes reach ingestion through an opaque controlled artifact reference.
- UI is non-authoritative and never processes content or constructs results.
- Existing writers/lifecycle govern state; safe read models show progress.
- Failures are auditable, bounded, replayable, and non-reflective.
- Upload never triggers export, ERP, OCR, or LLM.
- No production mode activates without storage/security/operations approval.

## 22. Phase 1 Implementation Record

Phase 1 adds the isolated standard-library-only `src/upload_runtime/` contract foundation: fixed source/file-type/status/error catalogs, immutable JSON-safe upload commands, validation policy/issues/results, safe artifact and processing-intent contracts, safe operation results/errors, domain-separated SHA-256 idempotency keys, and a structural staging port. Validation deterministically covers tenant/actor presence, filename traversal/safety/length, allowlisted and unsafe extensions, empty/maximum size, and declared MIME compatibility. Raw bytes, content, paths, credentials, claims, stack traces, nested metadata, API/runtime service behavior, staging I/O, ingestion, persistence, UI, OCR/LLM, export, and ERP remain absent. The focused suite passes 46 tests.

## 23. Phase 2 Implementation Record

Phase 2 adds guarded API contracts for `POST /api/v1/documents/upload`, `GET /api/v1/uploads`, and `GET /api/v1/uploads/{upload_id}`. Because no staging implementation exists and multipart support would add transport/dependency complexity, POST accepts strict JSON metadata only. Disabled auth returns `upload_staging_not_enabled`; authenticated local/demo requests require API-owned tenant scope and `document:ingest`, run Phase 1 validation, return safe fixed validation issues when invalid, and still return HTTP 503 staging unavailable when valid. GET routes use an app-scoped bounded tenant-filtered placeholder provider. No bytes are accepted or persisted, and no staging, ingestion, Document State, export, ERP, OCR/LLM, filesystem, database, network, or UI behavior is added. The API suite passes 103 tests with 9 optional transport skips.

## 24. Phase 3 Implementation Record

Phase 3 adds deterministic activation over a validated command and matching opaque `UploadArtifactReference`. It defines safe ingestion and received-document writer intents, fixed processing outcomes, opaque command/reference binding, safe receipts, and structural ingestion/Document State adapter ports. The service derives stable upload/document/source-event identities, calls the writer port before the ingestion-request port, preserves tenant/actor attribution, reports received lifecycle state only after a positive writer receipt, and safely maps rejection or exceptions. Missing staging returns `deferred_staging_required`; invalid validation or mismatched artifacts call no ports. Only test-local fakes invoke the ports. No concrete staging, ingestion pipeline, Document State writer/lifecycle adapter, API activation, path resolution, persistence, or processing execution is added because Phase 2 supplies no trusted artifact reference. Upload Runtime passes 62 tests and API passes 105 tests with 9 skips.

## 25. Phase 4 Implementation Record

Phase 4 adds immutable JSON-safe upload progress summaries, stages, events, timelines, failures, document links, and pages. A distinct read-status vocabulary preserves the exact Phase 3 activation contract. Ordered stages and approximate percentages are deterministic; percentage is omitted when source facts are insufficient, and no unrecorded stage is represented as completed. Pure projections accept only safe upload/activation/provider facts, while an in-memory query service provides tenant-scoped upload, document, timeline, and bounded recent-upload reads. The app-scoped provider exposes guarded `GET /uploads/{upload_id}/progress`, optional timeline, and `GET /documents/{document_id}/processing-status` envelopes. Reads neither activate ingestion nor mutate lifecycle, staging, export, or persistence.

## 26. Phase 5 Implementation Record

Phase 5 adds the FlowSync `/uploads` navigation and page while preserving the v0.17 shell and theme. File selection projects only filename, size, extension, and browser content-type metadata; the selected file object is not retained or transmitted. An explicit `Validate upload` action sends JSON to the guarded metadata endpoint, maps staging-disabled and validation issues to fixed safe copy, and never claims staging or processing. Recent uploads, progress, timelines, and document processing status use strict allowlisted parsers, API-owned access decisions, supplied events only, approximate labels only when provided, empty/error states, and manual refresh. Dependency-free validation rejects content-reading/encoding and binary/multipart transmission patterns. No backend, storage, ingestion, lifecycle, export, ERP, OCR/LLM, Streamlit, or competitor-price behavior is added.

## 27. Phase 6 Closure Record

Phase 6 creates the final architecture summary, handoff, and release notes; aligns the plan, implementation plan, ADR, roadmap, technical debt, changelog, and FlowSync guidance; and closes v0.19 pending the owner tag `v0.19-upload-processing-activation`. Closure records the previously passing 1,777-test repository baseline, focused suite counts, successful FlowSync validation/typecheck/build, compliant boundary verification, and the absence of raw-file transmission. No source code, tests, API/UI behavior, dependency, migration, staging, ingestion execution, export, ERP, OCR/LLM, Streamlit, dashboard, or competitor-price behavior changes in Phase 6.
