# Export Runtime / ERP Integration Boundary v1 Implementation Plan

**Milestone:** v0.18
**Status:** Phases 1-4 implemented and verified; Phase 5 not started

## 1. Milestone Overview

Implement a deterministic export runtime and integration boundary before enabling any real ERP connection or public export action. The runtime will reuse existing security, tenant, Document State, lifecycle, audit, idempotency, and platform composition boundaries through narrow injected ports. Each phase is one Codex session and stops before the next.

No implementation phase may let API routes or UI components call adapters or repositories directly. Real ERP dependencies and credentials remain out of scope.

## 2. Global Requirements

- Keep core export contracts immutable, JSON-compatible, privacy-safe, and deterministic.
- Require `document:export` and verified tenant scope before payload construction.
- Keep export operation status separate from `DocumentStatus`.
- Persist/claim an attempt before adapter invocation.
- Advance to `exported` only after a confirmed result is recorded.
- Make duplicate prevention atomic and replay-safe.
- Inject adapters, repositories, security, audit, and lifecycle services explicitly.
- Preserve existing API/UI behavior until a separately gated Phase 5 activation.
- Add no vendor SDK, network dependency, raw payload storage, or silent fallback.

## 3. Phase 1: Contracts And Status / Readiness Model

**Completion:** Implemented. The standard-library-only package provides fixed catalogs, immutable JSON-safe target/permission/readiness/payload/attempt/result/lifecycle/audit contracts, bounded privacy validation, canonical payload fingerprinting, domain-separated SHA-256 idempotency keys, fixed safe errors, and a runtime-checkable structural adapter port. It contains no evaluator, mapper registry, repository, service, adapter implementation, API/UI integration, persistence, I/O, or external dependency. The focused suite passes 38 tests; API, Platform Runtime, Security, Document State, Query Facade, Review Runtime, and boundary regressions pass unchanged.

### Scope

Create the dependency-light export domain contracts, error catalog, status catalog, readiness policy, and structural ports. No repositories, adapters, service orchestration, API routes, or UI changes.

### Expected Files

Create:

- `src/export_runtime/__init__.py`
- `src/export_runtime/contracts.py`
- `src/export_runtime/statuses.py`
- `src/export_runtime/readiness.py`
- `src/export_runtime/payloads.py`
- `src/export_runtime/attempts.py`
- `src/export_runtime/results.py`
- `src/export_runtime/idempotency.py`
- `src/export_runtime/errors.py`
- `src/export_runtime/ports.py`
- `tests/export_runtime/test_statuses.py`
- `tests/export_runtime/test_readiness_contracts.py`
- `tests/export_runtime/test_payload_contracts.py`
- `tests/export_runtime/test_attempt_result_contracts.py`
- `tests/export_runtime/test_idempotency.py`
- `tests/export_runtime/test_error_privacy.py`
- `tests/export_runtime/test_ports_and_boundaries.py`

Modify documentation status only.

### Deliverables

- `ExportTarget`, `ExportReadinessResult`, `ExportAttempt`, `ExportResult`, `ExportAuditIntent`, `ExportPermission`, and `ExportLifecycleDecision`.
- Fixed export status and failure/reason catalogs.
- Pure ordered readiness policy over injected safe projections.
- Read-only/read-write attempt/result ports, target catalog port, adapter port, and narrow authorization/lifecycle/audit intent ports.
- Metadata allowlist and bounded scalar validation.

### Tests

- Immutable/JSON-compatible contracts and deterministic serialization.
- Status/reason validation and unknown-value rejection.
- Every readiness check, order, denial, and successful result.
- Privacy rejection for raw payload-like or credential-like fields.
- Structural read-only/write port separation.
- Forbidden import checks.

### Verification

```text
python -m pytest tests/export_runtime -q
python -m pytest tests/security tests/document_state/lifecycle -q
python scripts/verify_boundaries.py
python -m py_compile src/export_runtime/contracts.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after contract/readiness/payload/idempotency foundation verification. Do not implement payload mapping, repositories, services, adapters, API, or UI integration.

## 4. Phase 2: Payload Builder And Idempotency Policy

**Completion:** Implemented. Phase 2 provides a pure safe-command payload builder, deterministic normalization, domain-separated canonical SHA-256 fingerprints, idempotency policy helpers, and `payload_invalid` readiness linkage. Unsafe/raw-shaped inputs receive fixed privacy-safe failures. No mapper plugin, repository, service, adapter, API/UI integration, persistence, I/O, or external dependency was added. The combined focused suite passes 73 tests; all required compatibility and boundary suites pass unchanged.

### Scope

Add pure canonical payload building, schema validation, fingerprinting, and deterministic idempotency derivation. No adapter invocation or persistence.

### Expected Files

Create:

- `src/export_runtime/builder.py`
- `src/export_runtime/fingerprints.py`
- `src/export_runtime/normalization.py`
- `src/export_runtime/policy.py`
- `tests/export_runtime/test_payload_builder.py`
- `tests/export_runtime/test_payload_fingerprints.py`
- `tests/export_runtime/test_idempotency_policy.py`
- `tests/export_runtime/test_payload_builder_privacy.py`
- `tests/export_runtime/test_export_phase2_boundaries.py`

Modify Phase 1 exports/contracts only when required by verified design gaps.

### Deliverables

- Safe `ExportPayloadBuildCommand`, deterministic builder, and fixed build results.
- Pure normalization of supplied structured values; no inference or accounting calculation.
- Canonical JSON serialization and SHA-256 content fingerprint.
- Domain-separated idempotency digest over tenant/document/version/target/schema/fingerprint.
- Idempotency policy over safe tenant/document/target/fingerprint/operation inputs.
- Payload validity linkage to the existing `payload_invalid` readiness issue.

### Tests

- Stable field ordering, repeatable payload/fingerprint, and schema-version behavior.
- Rejection of raw documents, rows, corrections, artifacts, credentials, paths, claims, and unsafe metadata.
- Distinct keys for tenant, document version, target, schema, and payload changes.
- Same operation produces same key.
- Builder does not mutate inputs or call repositories/adapters.

### Verification

```text
python -m pytest tests/export_runtime -q
python scripts/verify_boundaries.py
python -m py_compile src/export_runtime/builder.py
python -m py_compile src/export_runtime/fingerprints.py
python -m py_compile src/export_runtime/policy.py
python -m py_compile src/export_runtime/normalization.py
python -m py_compile src/export_runtime/idempotency.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after deterministic payload/idempotency verification. Do not invoke adapters.

## 5. Phase 3: Attempt / Result Repository Integration

**Completion:** Implemented with persistence-neutral Protocols and deterministic in-memory support only. Separate reader/writer views share a lock-protected store; attempt IDs and idempotency keys are unique; result writes require an existing matching attempt and allow only one immutable terminal result per attempt; status updates use expected-version compare-and-swap and a fixed transition catalog; queries are bounded, stable, and privacy-safe. Strict duplicate detection uses the same idempotency key, while same document-target activity is a separate optional helper. No SQLite migration, Document State adapter, service, lifecycle mutation, API/UI integration, or external dependency was added. The focused suite passes 110 tests and required compatibility suites pass unchanged.

### Scope

Implement persistence-neutral attempt/result repositories and deterministic in-memory support first. If durable SQLite integration is approved, add explicit Document State records/repositories and an additive migration behind export ports in this phase; do not expose them to API/UI.

### Expected Files

Create:

- `src/export_runtime/repositories.py`
- `src/export_runtime/store.py`
- `src/export_runtime/queries.py`
- `src/export_runtime/repository_errors.py`
- `tests/export_runtime/test_export_repositories.py`
- `tests/export_runtime/test_export_store.py`
- `tests/export_runtime/test_export_queries.py`
- `tests/export_runtime/test_export_repository_privacy.py`
- `tests/export_runtime/test_phase3_boundaries.py`

### Deliverables

- Atomic idempotency claim and duplicate lookup.
- Append-oriented attempts and immutable terminal results.
- Optimistic attempt-status transitions.
- Deterministic tenant/target/status/document filters and bounded pagination.
- Existing retry lineage fields and safe future reconciliation support.
- In-memory durability-neutral test composition.

### Tests

- Concurrent equal claims cannot both succeed.
- Duplicate successful/active operations return existing state safely.
- Retryable failure creates linked attempt; unknown delivery blocks blind retry.
- Immutable returns and no internal-state leakage.
- Fixed safe repository errors and recursive boundary/privacy checks.
- No SQLite or migration behavior in Phase 3.

### Verification

```text
python -m pytest tests/export_runtime -q
python -m pytest tests/api/document_intelligence tests/platform_runtime tests/security tests/document_state -q
python -m pytest tests/workflow_runtime/query_facade tests/review_runtime tests/ui/streamlit -q
python scripts/verify_boundaries.py
python -m py_compile src/export_runtime/repositories.py
python -m py_compile src/export_runtime/store.py
python -m py_compile src/export_runtime/queries.py
python -m py_compile src/export_runtime/repository_errors.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after repository/idempotency conformance. Do not add service orchestration or API routes.

## 6. Phase 4: Export Service, Placeholder Adapters, Audit, And Lifecycle

**Completion:** Implemented as an internal, standard-library-only orchestration boundary. `ExportRuntimeService` consumes caller-supplied safe readiness/identity facts, injected repositories and adapter, and the existing payload/idempotency foundation. It performs a simplified synchronous `preparing -> exporting -> terminal` sequence, records the terminal result before producing lifecycle intent, catches adapter exceptions into fixed safe failures, and blocks exact or active document-target duplicates before delivery. Audit and lifecycle are immutable returned intents only. Successful, failing, and unavailable placeholders perform no I/O. No platform composition, durable persistence, audit writer, Document State mutation, API/UI integration, public command, network, or real ERP behavior was added. The focused suite passes 133 tests; required compatibility suites pass unchanged.

### Scope

Implement the orchestration service with explicit dependencies, deterministic CSV/ERP placeholders, safe result mapping, audit intent, and lifecycle advancement. No real ERP, public endpoint, or enabled FlowSync action.

### Expected Files

Create:

- `src/export_runtime/service.py`
- `src/export_runtime/commands.py`
- `src/export_runtime/adapters/__init__.py`
- `src/export_runtime/adapters/placeholder.py`
- `src/export_runtime/audit.py`
- `src/export_runtime/lifecycle.py`
- `src/export_runtime/service_errors.py`
- `tests/export_runtime/test_export_service.py`
- `tests/export_runtime/test_placeholder_adapters.py`
- `tests/export_runtime/test_export_service_lifecycle.py`
- `tests/export_runtime/test_export_service_audit.py`
- `tests/export_runtime/test_export_service_privacy.py`
- `tests/export_runtime/test_phase4_boundaries.py`

Modify `src/platform_runtime/` only in a dedicated composition step if explicit export-runtime injection is approved.

### Deliverables

- `ExportRuntimeService.export()` using caller readiness, payload, claim, adapter, result, audit intent, and lifecycle intent.
- Deterministic successful, failing, and unavailable adapter placeholders.
- Recorded-success-first lifecycle intent with no projection mutation.
- Safe duplicate, adapter exception, repository error, and unavailable behavior.

### Tests

- Caller readiness denial occurs before payload or adapter access.
- Successful placeholder export records attempt/result then returns audit/lifecycle intents.
- Failed/unavailable adapter records failure without exported lifecycle.
- Duplicate calls do not invoke adapter twice.
- Exact and active document-target duplicates return safe transient duplicate results without redelivery or history overwrite.
- Adapter errors/results contain no raw exception/body/credential/path.
- In-memory and SQLite composition parity where available.

### Verification

```text
python -m pytest tests/export_runtime -q
python -m pytest tests/api/document_intelligence tests/platform_runtime tests/security tests/document_state -q
python -m pytest tests/workflow_runtime/query_facade tests/review_runtime tests/ui/streamlit -q
python scripts/verify_boundaries.py
python -m py_compile src/export_runtime/service.py
python -m py_compile src/export_runtime/commands.py
python -m py_compile src/export_runtime/adapters/placeholder.py
python -m py_compile src/export_runtime/audit.py
python -m py_compile src/export_runtime/lifecycle.py
python -m py_compile src/export_runtime/service_errors.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after internal export service verification. Do not add a public mutation route or real ERP connection.

## 7. Phase 5: API Mutation Boundary And FlowSync Readiness Placeholders

### Scope

Evaluate and, only after explicit owner approval, implement the authenticated API command boundary and read-only export history/readiness projections. FlowSync may add disabled/readiness/history presentation but must not enable delivery unless the API mutation contract and real session integration are approved.

### Candidate API Work

- `POST /api/v1/documents/{document_id}/export/prepare`
- `POST /api/v1/documents/{document_id}/export`
- `GET /api/v1/documents/{document_id}/exports`
- `GET /api/v1/export-attempts`
- `GET /api/v1/export-attempts/{attempt_id}`

POST activation requires authenticated-only mode, `document:export`, tenant/resource guards, bounded idempotency keys, standard envelopes, safe conflicts, no caller payload/credential/target URL, and app-scoped service injection. If these gates are not owner-approved, Phase 5 delivers contracts/documentation and disabled FlowSync placeholders only; route activation moves to the next milestone.

### Candidate FlowSync Work

- Readiness panel and safe reason codes.
- Export status badge and attempt history.
- Safe failure explanation and target/adapter label.
- Disabled export control until mutation support and session integration are active.

### Tests

- Mutation routes unavailable in disabled/unauthenticated modes.
- Permission and tenant denial before runtime invocation.
- Required idempotency key and safe `400/401/403/404/409/500` envelopes.
- No credentials/raw payload in request or response.
- Existing GET routes and read-only pages remain compatible.
- FlowSync never calls an adapter or computes permission/readiness locally.

### Verification

```text
python -m pytest tests/export_runtime tests/api/document_intelligence tests/security -q
python -m pytest tests/platform_runtime -q
python scripts/verify_boundaries.py
cd apps/flowsync-document-intelligence
npm run validate
npm run typecheck
npm run build
```

### Stop Condition

Stop after the approved API/UI boundary work. Do not connect a real ERP or proceed to closure automatically.

### Phase 5 Implementation Status

Implemented as a fail-closed contract boundary: safe tenant-filtered GET summaries are available, while prepare/export POST routes always return `mutation_not_enabled`. FlowSync provides only read-only readiness and attempt-history presentation with a disabled action. Runtime invocation, activation flags, request payload schemas, real adapters, persistence, and production delivery remain deferred.

## 8. Phase 6: Verification, Documentation, And Release Closure

### Deliverables

- Architecture summary and future-agent handoff.
- Release notes and recommended tag.
- Final plan/ADR/roadmap/debt/changelog status.
- Focused/full test, boundary, privacy, idempotency, lifecycle, API, and frontend evidence.
- Explicit list of inactive routes/adapters and deferred production work.

### Verification

Run focused export, security, Document State, lifecycle, Platform Runtime, API, and FlowSync checks plus boundary verification and full regression when practical. No real external call is permitted.

### Stop Condition

Stop after release documentation and verification. Do not commit, push, or tag unless explicitly instructed.

## 9. Boundary Requirements

- `export_runtime` core imports standard library and approved public contracts/ports only.
- API imports the export service through app-scoped dependency injection, never adapters/repositories.
- FlowSync imports HTTP contracts only.
- Adapters cannot import API/UI or decide security/readiness/lifecycle.
- Real vendor packages cannot leak into core contracts.
- Platform Runtime remains the only composition owner.

## 10. Backward Compatibility

- Existing GET paths, payload meanings, envelopes, request IDs, security headers, and read-only UI behavior remain unchanged until explicitly extended.
- Existing `DocumentStatus`, lifecycle transitions, and permission values are reused.
- Existing in-memory/SQLite behavior remains compatible unless additive export persistence is owner-approved and conformance-tested.
- No export behavior silently activates in local/disabled modes.

## 11. Risks And Mitigations

- **Unknown external outcome:** record reconciliation-required; never automatically resend.
- **Duplicate concurrent delivery:** atomic unique claim before adapter call.
- **Lifecycle conflict after success:** recorded success plus projection repair without redelivery.
- **Sensitive adapter leakage:** fixed error catalog, sanitization, and privacy tests.
- **Cross-tenant export:** default-deny guard, explicit active tenant, audited cross-tenant enablement.
- **Vendor coupling:** narrow port, separate adapter package, no vendor types in core.
- **Premature API/UI activation:** owner gate in Phase 5 and disabled placeholders by default.

## 12. Definition Of Done

- Phases 1-4 provide a deterministic, tested internal export boundary with no real ERP dependency.
- Readiness, payload, idempotency, attempts/results, adapters, audit, and lifecycle behavior are verified.
- Duplicate and unknown-delivery behavior cannot cause silent redelivery.
- Security and tenant scope are enforced before payload or adapter access.
- Only recorded confirmed success can advance lifecycle to `exported`.
- Any Phase 5 API/UI surface is explicitly approved, authenticated, safe, and still vendor-independent.
- Release documentation states exactly which adapters/routes remain placeholders or inactive.

## 13. Commit And Tag Strategy

Recommended owner-reviewed commits:

1. `feat: add export runtime contracts and readiness policy`
2. `feat: add export payload and idempotency foundation`
3. `feat: add export attempt and result repositories`
4. `feat: add export service and placeholder adapters`
5. `feat: add guarded export API boundary and readiness UI`
6. `docs: close v0.18 export runtime boundary`

Recommended final tag after Phase 6 owner review:

`v0.18-export-runtime-erp-integration-boundary`
