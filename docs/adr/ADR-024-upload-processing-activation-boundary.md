# ADR-024: Upload + Processing Activation Boundary

## Status

Accepted for v0.19. Phases 1-4 implement and verify the isolated contract foundation, guarded metadata API, deterministic activation/integration-port boundary, and tenant-scoped progress projections. Activation requires successful validation and a matching opaque artifact, produces safe ingestion and received-document intents, and calls only injected ports. Progress reads use immutable allowlisted facts, deterministic stage ordering, and concealed cross-tenant lookup. The API cannot supply an artifact and remains staging-disabled. No concrete storage, ingestion pipeline, Document State writer/lifecycle adapter, UI action, migration, dependency, or real processing execution is implemented yet.

## Context

The platform already has deterministic ingestion/parsing/validation components, ingestion and processing Document State writers, governed lifecycle advancement, tenant-aware security, Query Facade reads, and the FlowSync product UI. It lacks a safe public boundary that accepts raw file content, validates it, attributes it to a tenant/actor, activates ingestion, records progress, and returns privacy-safe status.

Putting file policy in FastAPI routes, parsing in FlowSync, or raw producer results in Document State would spread authority and expose content/path-rich data. The current ingestion pipeline is path-based, so activation also needs a private staging boundary without forcing a production storage choice.

## Decision

Create a transport-neutral `src/upload_runtime/` policy package for immutable upload contracts, deterministic validation, safe commands/results/errors, idempotency, and narrow ports. FastAPI owns multipart transport and authorization. A private staging port turns streamed content into an opaque artifact reference. A producer-side adapter resolves that reference for the existing ingestion pipeline and maps only safe results into existing Document State writer commands and lifecycle service calls.

```text
FlowSync
  -> API authorization + multipart transport
  -> Upload Runtime validation/orchestration
  -> private artifact staging port
  -> existing deterministic ingestion producer
  -> existing Document State writers + lifecycle
  -> Query Facade/API safe progress
  -> FlowSync timeline
```

## Package Decision

A separate upload package is selected because raw-input validation, upload identity/status, transport-neutral metadata, and ingestion activation are neither HTTP concerns nor persistence mapping. Integrating them directly into API/provider modules would make policy transport-specific. Adding them to Document State writers would give persistence ownership of raw content. Reusing `src/connectors/upload.py` is rejected because it accepts an already-materialized pandas DataFrame and is not a secure raw-file boundary.

## Type Decision

Evaluate activation of PDF, CSV, XLSX, TXT, and EML because deterministic loaders exist. Legacy XLS remains deferred initially. Each type requires explicit validation fixtures and resource/privacy limits. Browser-declared type and document-type selection are hints; server validation and ingestion classification are authoritative.

## Security Decision

Upload mutation requires authenticated identity, active tenant, and `document:ingest` unless a separately approved `document:upload` permission is introduced. Tenant/actor values come only from the authorization context. Service accounts need exact tenant scope. Cross-tenant upload is disabled. Default/unauthenticated and unsupported production composition fail closed. History/status reads are tenant-narrowed and unauthorized resource existence is concealed.

## File Safety Decision

Validate bounded sanitized filename, extension allowlist, empty/maximum size, unsafe/executable suffixes, traversal/control/reserved names, declared type consistency, practical file signature, and bounded metadata before ingestion. Stream bytes with enforced limits; do not base64-embed files in JSON. Production activation additionally requires malware scanning and storage/retention decisions, which remain deferred.

## Storage Decision

Do not force production storage in v0.19 planning. Define a staging port with opaque references. A test/in-memory or explicitly local/demo adapter may be implemented in later phases; production remains unavailable until encrypted durable storage, malware/quarantine, retention/deletion, backup/recovery, and access policy are approved. Private paths must never cross public contracts.

## Ingestion And Writer Decision

Use the existing deterministic ingestion pipeline first. No OCR or LLM fallback is permitted. Producer adapters project safe identities, counts, statuses, confidence, codes, timestamps, and opaque artifact references into existing writers; complete ingestion/parsing results never cross the writer boundary. Use stable event identities and existing idempotent/checkpoint semantics.

## Lifecycle Decision

Create tenant-owned document state at `received`, record stage progress, and advance to `ingested` only after recorded ingestion success through the existing lifecycle policy/service with expected version. Later actual producer stages may advance through parsed/extracted/transformed/validated/matched/review-required states. Do not fabricate stages and never advance to approved/export-ready/exported from upload. Failures remain safe, auditable, and replayable.

## API Decision

Evaluate `POST /api/v1/documents/upload`, `GET /api/v1/uploads`, `GET /api/v1/uploads/{upload_id}`, and `GET /api/v1/documents/{document_id}/processing-status`. The POST begins disabled-by-default and returns the standard envelope. API owns permission, tenant, IDs, validation invocation, capability state, and safe errors. Responses contain no raw content, path, claims, exceptions, or unrestricted metadata.

## FlowSync Decision

Preserve v0.17 visual identity. Before activation show disabled/unavailable state. After approved backend activation, FlowSync may submit selected content, safe source/type hints, display server validation, and read progress. It never processes content, establishes final type, constructs results, decides permissions/tenant, exposes paths, invokes export, or connects ERP.

## Privacy Decision

Exclude raw files, rows/text, payload bodies, parser/extraction output, raw multipart headers, credentials, tokens, claims, backend/staging paths, stack traces, raw errors, and unrestricted metadata from API/UI/Document State/audit projections. Filenames are sanitized and returned only where product need and authorization justify them.

## Failure Decision

Use fixed non-reflective codes including unsupported type, too large, empty, unsafe filename, type mismatch, invalid metadata, ingestion/parsing/extraction/validation/matching failure, and internal error. Record safe committed checkpoints. Retry uses stable identities; partial success is not rolled back or falsely reported as full success.

## Consequences

### Positive

- Raw-content policy has one reusable owner.
- API/security, ingestion, persistence, and UI responsibilities remain separated.
- Existing writers/lifecycle/read models are reused.
- Production storage and external processing are not prematurely selected.
- Privacy, replay, and failure behavior become testable before activation.

### Negative

- Path-based ingestion needs a controlled staging adapter.
- Synchronous local activation may not translate to production latency/scale.
- MIME/signature validation and malware scanning need future capability decisions.
- Partial multi-record progress still needs deterministic replay rather than distributed atomicity.

## Alternatives Rejected

- **Parse in FlowSync:** violates API authority and exposes processing logic/content in the browser.
- **Put all logic in the route:** couples policy to FastAPI and weakens testability/composition.
- **Pass raw bytes/results to Document State:** violates persistence/privacy boundaries.
- **Reuse DataFrame UploadConnector:** it is downstream structured-data input, not raw-file validation/staging.
- **Select production object storage now:** premature without deployment, threat, retention, and operations requirements.
- **Enable OCR/LLM fallback:** non-deterministic/external processing is outside v0.19.

## Deferred Decisions

Production storage and malware scanning, raw download, retention/legal hold, queue/outbox, retry workers/reconciliation, OCR/LLM, image/archive/batch/resumable uploads, legacy XLS, separate upload permission, production rate limits, and export/ERP integration.

## Acceptance

ADR-024 is accepted when owners approve `upload_runtime` as the raw-input policy boundary, API-authoritative auth/tenant behavior, opaque staging references, deterministic ingestion-first processing, reuse of governed writers/lifecycle, privacy rules, default-disabled activation, and the six-phase implementation plan.
