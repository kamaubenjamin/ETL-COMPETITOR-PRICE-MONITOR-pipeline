# ADR-023: Export Runtime / ERP Integration Boundary

## Status

Accepted for v0.18. Phase 1 implements and verifies the dependency-light contract boundary; service, persistence, adapter, API, and UI integration remain unimplemented.

## Context

The platform has governed document lifecycle state, tenant-aware authorization, internal writers, durable local repositories, a read-only API, and a read-only FlowSync UI. `document:export`, `approved`, `export_ready`, and terminal `exported` already exist, but there is no runtime that validates export readiness, builds a sanitized payload, prevents duplicates, records attempts/results, invokes an adapter, audits outcomes, and advances lifecycle after confirmed success.

Direct ERP calls from FlowSync, API routes, workflow writers, or repositories would distribute policy and bypass existing security, composition, audit, idempotency, and lifecycle boundaries.

## Decision

Create an independent `src/export_runtime/` domain boundary. It will own deterministic export readiness, payload construction, idempotency, attempt/result orchestration, adapter invocation, audit intent, retry classification, and lifecycle decision. It will consume explicit injected ports and will not own HTTP routing, UI behavior, credentials, vendor SDKs, database engines, or document processing.

Phase 1 confirms this boundary with standard-library-only immutable contracts, fixed catalogs, bounded scalar metadata, sanitized payload and result shapes, deterministic SHA-256 fingerprints/idempotency keys, fixed safe errors, and a structural adapter port. Existing runtime packages do not import `export_runtime`; no execution behavior is active.

The runtime and adapters are separate:

- Core runtime validates authority and state and produces sanitized target payloads.
- `ExportAdapterPort` receives only a validated payload and safe execution context.
- Real ERP adapters live in explicit integration packages and return structured sanitized results.
- Placeholder adapters may support deterministic tests but make no real external call.

## Readiness Decision

Authorization and tenant scope are evaluated before readiness and payload construction. Readiness requires a tenant-visible document, `document:export`, approved/export-ready lifecycle, non-blocking validation, required matching/review/entity summaries, an explicitly enabled target, no active/successful duplicate, and a valid safe payload.

Readiness results use stable ordered codes and do not expose raw values or internal policy data.

## Status And Lifecycle Decision

Export attempt status is distinct from `DocumentStatus`. The runtime may represent `not_ready`, `ready`, `preparing`, `queued`, `exporting`, `exported`, `failed`, `cancelled`, and `duplicate_prevented`, while reserving asynchronous states until a queue/cancellation model exists.

Payload preparation and failed delivery never mark a document exported. The adapter-confirmed result is recorded first. Only confirmed success may request the existing governed lifecycle transition to `exported`. If projection advancement conflicts, the result is retained and projection repair occurs without redelivery.

## Idempotency Decision

The server derives a domain-separated digest from tenant, document, document version, target, payload schema, and payload fingerprint. Attempt persistence claims that digest atomically before adapter invocation. Equivalent active or successful operations cannot invoke the adapter twice. Retries are explicit linked attempts; unknown delivery outcomes require reconciliation.

## Security Decision

Future export mutations require authenticated mode, `document:export`, and exact tenant/resource scope. Service accounts require explicit tenant scope and explicit permission. Platform-admin cross-tenant export requires explicit enablement and audit. Disabled/local unauthenticated mode cannot activate real export delivery.

The API remains authoritative. FlowSync may display readiness/history and submit a future approved command, but it never decides permission/readiness, broadens tenant scope, constructs payloads, supplies credentials, or calls an ERP.

## Persistence And Composition Decision

Core defines persistence ports for attempts/results. Platform Runtime injects repositories, security, readiness sources, lifecycle, audit, target catalog, adapters, and credential handles. A later Document State/SQLite adapter may implement durable storage through additive, conformance-tested records and migrations. API/UI never access repositories directly and missing adapters never fall back.

## Privacy Decision

Payloads, records, audit, logs, errors, API responses, and UI projections exclude raw documents, rows, protected correction values, unrestricted artifact payloads/metadata, credentials, tokens, claims, backend/storage paths, DSNs, stack traces, raw exceptions, and vendor request/response bodies. Adapter codes/messages and external references are bounded and sanitized.

## API And UI Decision

Potential prepare/export POST routes and export-history GET routes are planning candidates only. POST activation is gated on verified runtime, persistence, security, idempotency, audit, lifecycle, and owner approval. FlowSync export controls remain disabled until the API mutation and real identity/session boundary exist.

## Consequences

### Positive

- Export policy has one testable owner.
- UI and API cannot bypass tenant, permission, idempotency, or lifecycle rules.
- Vendor dependencies and credentials stay outside core contracts.
- Duplicate and uncertain delivery receive explicit safe behavior.
- CSV and ERP adapters can share one runtime contract without becoming equivalent production integrations.

### Negative

- Export requires new attempts/results persistence and composition work.
- External calls cannot share an atomic transaction with local state.
- Unknown delivery outcomes require reconciliation procedures.
- Public export actions remain unavailable until several prerequisite phases pass.

## Alternatives Rejected

### Call ERP directly from FlowSync

Rejected because the browser cannot own permissions, tenant scope, credentials, idempotency, audit, or lifecycle.

### Put export logic in API routes

Rejected because HTTP handlers are not a domain/runtime boundary and would couple policy to transport.

### Add export methods to workflow writers

Rejected because writers persist internal state and should not own external delivery protocols.

### Treat file export and ERP export as unrelated features

Rejected because both need the same readiness, payload, idempotency, attempt/result, audit, security, and lifecycle controls.

### Mark exported before adapter confirmation

Rejected because failure or timeout would create false lifecycle state.

## Deferred Decisions

- Real vendor selection, SDKs, schemas, credentials, and production network policy.
- PostgreSQL/Supabase persistence, outbox, queue/worker, and reconciliation implementation.
- Whether public mutation activation is included in v0.18 Phase 5 or a separate milestone.
- Export-specific read permission versus existing `audit:read`.
- CSV encryption, signing, retention, delivery, and download authorization.
- FlowSync authenticated action design and ERP-specific presentation.

## Acceptance

ADR-023 is accepted when owners approve `src/export_runtime/` as the policy/orchestration boundary, isolated adapters behind ports, readiness-before-payload behavior, atomic duplicate prevention, recorded-success-before-lifecycle behavior, default-deny tenant/security rules, privacy constraints, and gated API/UI activation.
