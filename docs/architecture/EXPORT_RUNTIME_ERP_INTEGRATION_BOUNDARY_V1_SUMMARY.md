# Export Runtime / ERP Integration Boundary v1 Summary

## Milestone Status

v0.18 is implemented, verified, and closed pending the owner tag `v0.18-export-runtime-erp-integration-boundary`.

The milestone delivers a deterministic, dependency-light export boundary without enabling production export delivery. It includes immutable export contracts and statuses, readiness and payload contracts, deterministic payload construction and normalization, payload fingerprints, idempotency policy, repository protocols, an in-memory attempt/result store, deterministic queries, duplicate prevention, `ExportRuntimeService`, no-I/O placeholder adapters, lifecycle decisions, audit intents, guarded API contracts, and a disabled/read-only FlowSync export placeholder.

## Delivered Architecture

```text
FlowSync Export Placeholder
  -> GET-only / disabled export API boundary
  -> Export provider
  -> Export Runtime Service
  -> Payload builder + idempotency policy
  -> Attempt/result repositories
  -> Placeholder adapter port
  -> Audit intents + lifecycle decisions
```

The arrows describe ownership and intended flow, not currently activated API execution. In v0.18 the API does not invoke `ExportRuntimeService`, construct payloads, or call adapters.

## Delivered Capabilities

- Fixed export status, operation, readiness, target, payload, attempt, adapter-result, result, lifecycle, and audit contracts.
- Pure readiness linkage and privacy-safe payload rejection.
- Deterministic normalization, payload building, SHA-256 fingerprinting, and domain-separated idempotency keys.
- Persistence-neutral attempt/result reader and writer protocols.
- Lock-protected process-local store with unique attempts and idempotency claims, optimistic transitions, immutable terminal results, and deterministic pages.
- Exact-key and active document-target duplicate prevention before adapter invocation.
- Injected synchronous service with safe commands/results and sanitized exception handling.
- Successful, failing, and unavailable deterministic placeholder adapters with no I/O.
- Bounded audit intents and pure lifecycle decisions; only stored confirmed success recommends `exported`.
- Safe export-history GET routes and disabled prepare/export POST contracts.
- FlowSync read-only readiness/history panel and permanently disabled export action.

## Export Runtime Boundary

`src/export_runtime/` imports only the Python standard library and package-local modules. It imports no API, FlowSync, Streamlit, Document State, Platform Runtime, Security, Workflow Query Facade, persistence/SQLite implementation, external service, or ERP SDK. Core owns policy and orchestration contracts; outer composition remains responsible for trusted identity/readiness inputs, repositories, adapters, writers, and delivery infrastructure.

## API Boundary

Current routes:

- `GET /api/v1/documents/{document_id}/exports`
- `GET /api/v1/export-attempts`
- `GET /api/v1/export-attempts/{attempt_id}`
- `POST /api/v1/documents/{document_id}/export/prepare`
- `POST /api/v1/documents/{document_id}/export`

GET routes expose bounded summaries through API-owned tenant scope. Both POST routes are disabled and return HTTP 503 with code `mutation_not_enabled`, message `Export execution is not enabled.`, and `activation: deferred`. The API constructs no export payload, invokes no adapter, and makes no ERP call in this release. Tenant and security decisions remain API-authoritative.

## FlowSync Boundary

FlowSync preserves the approved v0.17 dark-green sidebar, white workspace, calm enterprise layout, and green semantic accents. It displays the export-readiness placeholder, disabled export action, safe unavailable state, and safe history when available. It sends no export POST request, constructs no `ExportPayload`, decides no permission, and exposes no raw payload.

## Privacy And Safety

Public records, errors, audit intents, API summaries, and UI projections exclude raw documents, raw rows, raw payload bodies, raw adapter responses, credentials, tokens, raw claims, backend paths, stack traces, and unrestricted metadata. Tenant IDs are not returned in public export summaries; tenant narrowing occurs before projection.

## Verification

- Export Runtime: 133 passed.
- Document Intelligence API: 87 passed, 9 skipped.
- Platform Runtime: 84 passed.
- Security: 60 passed.
- Document State: 330 passed.
- Workflow Query Facade and Review Runtime: 239 passed.
- Streamlit UI: 64 passed.
- Full repository regression: 1,675 passed, 9 skipped.
- FlowSync validation, strict typecheck, and production build passed.
- Runtime boundary verification reported compliant.

## Deferred Work

Real mutation activation, production authentication for export, durable persistence, transactional outbox/queue processing, real ERP adapters, CSV/file delivery policy, credential management, reconciliation, retry workers, lifecycle and audit writers, an enabled FlowSync action, upload-to-export integration, and an external test adapter remain deferred.

