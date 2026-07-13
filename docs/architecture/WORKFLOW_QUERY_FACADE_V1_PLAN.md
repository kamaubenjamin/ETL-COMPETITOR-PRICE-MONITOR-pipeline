# Workflow Query Facade v1 Plan

**Milestone:** v0.10
**Status:** Proposed; implementation not started

## 1. Problem Statement

v0.9 provides a stable read-only Document Intelligence API, but its data is supplied by deterministic API-owned preview fixtures. Live API reads cannot import Document Engine, Entity, Transform, Matching, Review, storage, telemetry, UI, Streamlit, FlowSync, or competitor-price internals without violating runtime boundaries and distributing query composition across transport handlers.

v0.10 introduces a Workflow-owned read facade between the API and approved runtime read sources. The facade publishes stable, privacy-safe read models and deterministic query behavior while leaving runtime state and execution ownership unchanged.

## 2. Goals

1. Define one public Workflow-owned query boundary for Document Intelligence live-state projections.
2. Preserve v0.9 endpoint payload meanings, envelope fields, privacy rules, request IDs, and pagination behavior.
3. Define stable read models for documents, processing, validation, matching, reviews, corrections, reprocess plans, workflow runs, and audit.
4. Keep all v0.10 operations read-only, deterministic, bounded, and JSON-compatible.
5. Allow API Runtime to depend only on the facade's public surface.
6. Prove the boundary first with a deterministic in-memory provider and API adapter.
7. Define narrow source ports for future live adapters without importing runtime implementations.

## 3. Non-Goals

- Live database, repository, cache, event-stream, or search-index implementation.
- Runtime mutation, workflow execution, upload, correction, decision, reprocess, or export commands.
- Authentication, authorization, tenant isolation, rate limiting, gateway, TLS, or production CORS.
- API endpoint or envelope changes.
- Streamlit or FlowSync UI changes.
- OCR, LLM processing, external services, telemetry instrumentation, or competitor-price integration.
- A generic reporting/data-access layer for unrelated products.

## 4. Package Location Decision

Use:

```text
src/workflow_runtime/query_facade/
```

### Why This Location

- Workflow Runtime already owns orchestration-level state and is the only runtime API Runtime may consume under R05.
- The package name makes ownership and dependency direction explicit.
- It keeps API contracts separate from runtime-neutral query contracts.
- It avoids creating an ownerless top-level integration layer.
- It does not imply that Document Intelligence owns underlying runtime state.

### Alternatives Considered

| Location | Decision |
|---|---|
| `src/workflow_runtime/query_facade/` | Selected: aligns with R05 and orchestration ownership. |
| `src/query_facade/` | Rejected: ambiguous ownership and likely to become a general cross-runtime dumping ground. |
| `src/document_intelligence/query_facade/` | Rejected: creates a new domain runtime and obscures the approved API-to-Workflow dependency direction. |

## 5. Proposed Architecture

```text
Streamlit / future FlowSync Document Intelligence
                    |
                    v
        Document Intelligence API v1
                    |
                    v
   Workflow Runtime public query facade
     | contracts | service | source ports |
                    |
                    v
 Approved injected read-source implementations
                    |
                    v
 Runtime-owned read models / workflow execution state
```

The API adapter translates facade records into the existing v0.9 provider interface. API routers continue to own HTTP validation and envelopes. The facade owns query semantics, projection contracts, deterministic ordering, pagination inputs/results, and privacy-safe composition. Source runtimes continue to own state.

## 6. Proposed Package Structure

```text
src/workflow_runtime/query_facade/
  __init__.py
  contracts.py
  errors.py
  filters.py
  ports.py
  service.py
  memory.py
```

- `contracts.py`: immutable JSON-compatible read models and page results.
- `filters.py`: bounded typed filter/page contracts.
- `ports.py`: narrow read-only protocols for injected sources.
- `service.py`: facade orchestration, ordering, pagination, and safe composition.
- `memory.py`: deterministic in-memory v1 provider used by tests and preview integration.
- `errors.py`: stable path/code errors without source payloads.
- `__init__.py`: intentionally small public export surface.

## 7. Read Model Contracts

All records are immutable or defensively copied, serialize to plain JSON-compatible dictionaries, use UTC ISO-8601 timestamps, and contain bounded strings/scalars only.

### Shared Contracts

- `QueryPageRequest`: `limit`, `offset` with v0.9-compatible defaults and maximums.
- `QueryPage[T]`: `items`, `total`, `limit`, `offset`, `snapshot_at`.
- `QuerySort`: fixed field and direction allowlists; no arbitrary expressions.
- Stable errors: `code`, safe message, optional bounded field name.

### Document Inbox

- `document_id`, `filename`, `document_type`, lifecycle `status`, `confidence`, `current_stage`, `received_at`.
- Filters: status and document type.
- Order: `received_at`, then `document_id`.

### Processing Status

- `document_id`, `stage`, `status`, `occurred_at`.
- Order: `occurred_at`, then stage.

### Validation Issue

- `issue_id`, `document_id`, `severity`, `field`, `rule_id`, `code`, safe message.
- No raw invalid value or source row.
- Order: severity rank, field, rule ID, issue ID.

### Matching Result

- `match_id`, `document_id`, `entity_type`, safe candidate ID, confidence, status.
- No raw master record or unrestricted candidate metadata.
- Order: confidence descending, then candidate ID and match ID.

### Review Case Summary

- `review_case_id`, `document_id`, reason code, priority, status, assigned reviewer ID, correction count, decision code, reprocess state, created/updated timestamps.
- Filters: status and priority.
- No controlled correction values or reviewer comments.

### Correction History Summary

- `correction_id`, `review_case_id`, field path, operation, reason code, actor ID, occurred timestamp, source stage.
- Explicitly excludes old/new controlled values and full payloads.

### Reprocess Plan Summary

- `plan_id`, `review_case_id`, from/target stages, invalidated/retained counts, reason code, requester ID, created timestamp, dry-run mode.
- No artifact contents or unbounded artifact lists.

### Workflow Run Summary

- `run_id`, workflow name, status, start/end timestamps, duration, safe stage counts.
- Filters: status and workflow name.
- Order: start timestamp descending, then run ID.

### Audit Event Summary

- `event_id`, event type, actor ID, optional document/review reference, occurred timestamp, allowlisted safe metadata.
- Filters: event type and bounded references.
- No exception, payload, raw value, credential, or unrestricted metadata.

## 8. Query Facade Interface

The public service should provide explicit methods rather than a generic query language:

```text
list_documents(filters, page)
get_document(document_id)
list_processing(document_id, page)
list_validation_issues(document_id, page)
list_matching_results(document_id, page)
list_review_cases(filters, page)
get_review_case(review_case_id)
list_correction_history(review_case_id, page)
list_reprocess_plans(filters, page)
list_workflow_runs(filters, page)
list_audit_events(filters, page)
```

No generic SQL, arbitrary field selection, dynamic callbacks, plugin discovery, or mutation method is allowed.

## 9. Source Port Model

`ports.py` defines small read-only protocols grouped by ownership concern, such as document projections, validation/matching projections, review projections, workflow run state, and safe audit projections.

Rules:

- The facade package imports protocols and facade contracts only.
- It does not import runtime repositories, services, stores, models, or telemetry.
- Future runtime-owned adapters implement these ports behind public boundaries.
- Composition injects adapters into the facade; the facade never discovers runtimes dynamically.
- Missing optional sources return an explicit unavailable result/error, never partial silent substitution.
- Cross-source snapshot consistency remains explicit in page metadata and is not overstated as transactional.

## 10. Determinism And Pagination

- Every collection has a documented total order with an ID tie-breaker.
- Apply filters before counting and pagination.
- Default limit is 50; maximum remains 200 to match v0.9.
- Offset is non-negative; invalid filters and bounds fail deterministically.
- Repeated reads against the same snapshot produce identical item order and totals.
- Provider inputs and outputs are never mutated.
- Cursor pagination is deferred until live volume and consistency requirements are known.

## 11. Privacy And Security

- Contracts use explicit allowlists; arbitrary metadata is rejected or reduced to approved scalar keys.
- No documents, complete rows, correction values, comments, credentials, stack traces, file paths, or internal exceptions cross the facade.
- Errors identify safe codes/fields/IDs only and do not echo payloads.
- Query source failures are mapped to stable facade errors.
- The API retains responsibility for request IDs, HTTP status mapping, security headers, CORS, and envelopes.
- Auth, tenant filtering, and policy enforcement are required before production live reads and remain deferred from v0.10.

## 12. API Integration Model

Phase 3 adds an API-side provider implementing the current read-provider methods by calling only the public Workflow Query Facade. Existing routers, paths, filters, response envelope, pagination metadata, and payload meanings remain unchanged.

The API-owned deterministic provider remains available for isolated tests during migration. Provider selection must be explicit; a configured facade provider must not silently fall back to preview fixtures. Streamlit continues to consume the API and does not import the facade.

## 13. Boundary Rules

- `src/api/document_intelligence/` may import only the public `src.workflow_runtime.query_facade` surface, its own package, standard library, and existing FastAPI/Starlette dependencies.
- `query_facade/` must not import Document Engine, Entity Runtime, Transform Runtime, Matching Runtime, Review Runtime, storage, telemetry, API, UI, Streamlit, FlowSync, or competitor-price internals.
- Runtime-owned future adapters may depend inward on their own public read services and implement facade ports; adapter wiring must occur in an approved composition boundary.
- No reverse dependency from Workflow Query Facade to API contracts.
- No new boundary exemption is acceptable for v0.10.

## 14. Testing Strategy

- Contract construction, strict validation, JSON round trips, and immutability.
- Stable ordering, filtering, pagination, totals, empty results, and defensive copying for every read model.
- Missing IDs, invalid filters, unavailable sources, and privacy-safe errors.
- Explicit scans proving controlled values/raw payloads are absent.
- API provider parity against v0.9 payload meanings and envelopes.
- OpenAPI path/method snapshots proving no endpoint or mutation change.
- Static import/boundary tests with no new exemptions.
- Existing API, Streamlit, Review Runtime, Workflow Runtime, and full regression suites.

## 15. Risks And Open Questions

| Risk / question | Planned response |
|---|---|
| Facade becomes a cross-runtime dumping ground | Narrow ports, explicit methods, import bans, and no dynamic discovery. |
| Multiple sources cannot provide one transactionally consistent snapshot | Expose snapshot metadata honestly; define stronger consistency only with durable sources. |
| API and facade models drift | Contract parity tests; API adapter performs explicit translation. |
| Offset pagination becomes unstable at scale | Keep deterministic v1 semantics; evaluate cursors with live requirements. |
| Tenant data could mix in future live reads | Do not enable production live provider until tenant/auth policy exists. |
| Audit ordering differs across sources | Require normalized UTC timestamps and stable event-ID tie-breakers. |
| Ownership of future adapter composition is unclear | Resolve in a follow-up deployment/composition ADR before live integration. |

## 16. Definition Of Done

- Public Workflow Query Facade contracts and explicit read-only service exist under the selected package.
- All nine read-model areas are represented with bounded JSON-compatible contracts.
- Deterministic in-memory provider passes ordering, pagination, privacy, and immutability tests.
- API can use a facade-backed provider without changing v0.9 routes, envelopes, or payload meanings.
- No mutation, database, auth, UI, OCR, LLM, external service, competitor coupling, or direct runtime-internal import is introduced.
- Boundary verifier passes without new exemptions.
- Focused and full regressions pass and release documentation is complete.
