# Upload + Processing Activation v1 Summary

## Milestone Status

v0.19 is implemented, verified, and closed pending the owner tag `v0.19-upload-processing-activation`.

The milestone establishes a safe upload policy, activation-intent, progress-read, API, and FlowSync boundary without enabling raw-file transfer, staging, or ingestion execution. The public mutation remains a guarded JSON metadata-validation preview. Real production upload processing is explicitly deferred.

## Delivered Architecture

```text
FlowSync upload preview
  -> Guarded upload metadata API
  -> Upload Runtime validation
  -> Opaque staging boundary
  -> Activation intents
  -> Ingestion / Document State adapter ports
  -> Progress projections
  -> FlowSync timeline
```

The arrows after validation describe the controlled contract and intended composition boundary. They do not claim that staging, ingestion, or Document State adapter execution is activated in v0.19.

## Delivered Capabilities

- Standard-library-first `upload_runtime` contracts, validation, commands, results, fixed errors, and status catalogs.
- Deterministic upload idempotency and opaque staged-artifact reference contracts.
- Structural staging, ingestion-activation, and Document State writer ports.
- Guarded metadata-only upload API with API-authoritative identity, tenant scope, and `document:ingest` permission enforcement.
- Controlled activation service requiring successful validation and a matching opaque artifact reference.
- Safe ingestion activation and received-document state write intents with deterministic upload, document, and source-event identities.
- Immutable processing progress summaries, stages, events, timelines, failures, document links, and bounded pages.
- Deterministic progress projections, tenant-scoped in-memory queries, concealed cross-tenant reads, and safe failure mapping.
- FlowSync `/uploads` page, browser-local metadata selection, explicit validation preview, recent uploads, supplied-event timeline, manual refresh, and document processing-status panel.
- Dependency-free frontend checks proving no file-content reading, encoding, binary, or multipart transmission implementation exists.

## Current API Boundary

- `POST /api/v1/documents/upload`
- `GET /api/v1/uploads`
- `GET /api/v1/uploads/{upload_id}`
- `GET /api/v1/uploads/{upload_id}/progress`
- `GET /api/v1/uploads/{upload_id}/timeline`
- `GET /api/v1/documents/{document_id}/processing-status`

The POST accepts JSON metadata only. It accepts no multipart body or raw bytes, performs no staging, activates no ingestion, and triggers neither export nor ERP. Valid authorized metadata reaches the governed staging-disabled outcome. Disabled or unavailable staging returns `upload_staging_not_enabled` without claiming that a document was uploaded or processed.

## FlowSync Boundary

FlowSync preserves the approved v0.17 dark-green sidebar, white workspace, calm enterprise layout, existing typography, and restrained green semantic accents. The selected file remains in the browser. Only filename, size, inferred extension, and browser-reported content type are sent after the explicit **Validate upload** action. The interface never calls the action “Upload and process.”

Recent upload and processing views are API-owned. Timelines render only events supplied by the API, percentage is shown only when supplied and is labeled approximate where indicated, and refresh is manual. FlowSync performs no tenant or permission decision.

## Privacy And Safety

Public contracts, provider projections, errors, and UI state exclude raw bytes/content, filesystem or backend paths, unrestricted metadata, credentials, tokens, claims, stack traces, and raw exceptions. The UI exposes no tenant or actor controls. Progress events are never fabricated, and the client does not construct backend commands or processing outcomes.

No staging, ingestion execution, OCR/LLM, raw preview/download, export activation, ERP connection, dependency, migration, Streamlit, dashboard, or competitor-price behavior was added.

## Verification Evidence

- Upload Runtime: 78 passed.
- Document Intelligence API: 111 passed, 9 skipped.
- Export Runtime: 133 passed.
- Platform Runtime: 84 passed.
- Security: 60 passed.
- Document State: 330 passed.
- Workflow Query Facade and Review Runtime: 239 passed.
- Full repository regression previously passed: 1,777 passed, 9 skipped.
- FlowSync `npm run validate`: passed across 64 frontend source files.
- FlowSync `npm run typecheck`: passed.
- FlowSync `npm run build`: passed.
- Source scan: no raw-file transmission implementation found.
- Runtime boundary verification: compliant.
- `git diff --check`: passed with existing line-ending warnings.

## Deferred Work

Trusted staging adapter, multipart/raw-file API transport, private durable object/file storage, malware scanning and quarantine, real ingestion adapter execution, durable upload/progress repository, async queue/outbox/workers, retry and reconciliation, live authenticated end-to-end testing, desktop/mobile rendered browser verification, OCR/LLM, raw preview/download, and export activation remain deferred.

## Recommended Next Milestone

Proceed with **v0.20 Business Workflow / Rules Studio planning**. Keep production upload staging and ingestion activation as a separate explicit production-readiness track; do not hide that work inside Workflow Studio scope.

