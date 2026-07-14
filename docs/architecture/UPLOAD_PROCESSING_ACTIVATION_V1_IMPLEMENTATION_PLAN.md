# Upload + Processing Activation v1 Implementation Plan

**Milestone:** v0.19
**Status:** Implemented, verified, and closed pending owner tag

## 1. Delivery Rules

Implement one phase per reviewed change. Every phase stops after its focused and compatibility verification. No phase may silently activate production upload, bypass API authorization, expose raw content/paths, trigger export, connect ERP, or add OCR/LLM. Real storage, dependencies, and migrations require separate approval.

## 2. Phase 1: Upload Contracts, Validation, And Command Model

**Status:** Complete. The standard-library contract package, deterministic validation, safe commands/results/errors, opaque references, idempotency policy, staging Protocol, privacy checks, and recursive boundary tests are implemented. No staging implementation or outer integration was added.

### Deliverables

- Create standard-library-first `src/upload_runtime/` contracts, validation, commands, results, errors, and ports.
- Fixed upload/validation/status/failure catalogs.
- Immutable safe filename/file descriptor/upload metadata/validation result/accepted upload/ingestion activation command contracts.
- Pure allowlist, filename, empty, size, extension/type consistency, and metadata validation.
- Content digest/idempotency policy over streamed bytes without storing content in contracts.
- Opaque artifact reference contract; no path or raw bytes in serialization.

### Decisions To Lock

- Initial candidate allowlist: PDF, CSV, XLSX, TXT, EML; legacy XLS deferred.
- Per-format and global size limits.
- Filename normalization and extension/type/signature rules.
- `document:ingest` reuse versus separate permission proposal (do not change catalog without approval).

### Tests

Contract immutability/serialization, valid formats, every rejection reason, filename traversal/control/reserved-name cases, empty/oversize, metadata privacy, deterministic digest/idempotency, opaque reference privacy, recursive imports, and no API/engine/writer/export/ERP imports.

### Stop Condition

No API route, staging implementation, ingestion call, writer call, or UI.

## 3. Phase 2: Guarded API Upload Boundary

**Status:** Complete as a fail-closed metadata-only contract. Safe GET summaries and strict JSON metadata validation are registered; mutation requires authenticated tenant-scoped `document:ingest` where auth is enabled and always ends with staging unavailable. Multipart bytes and staging remain deferred.

### Deliverables

- Guarded JSON metadata POST contract and upload history/detail GET contracts; multipart remains deferred.
- API-local schemas/projections matching the existing response envelope.
- App-scoped upload provider/service port; disabled placeholder by default.
- Authentication, active tenant, `document:ingest`, service-account, concealment, request/idempotency, size, and rate-control hooks.
- Safe fixed errors; no raw body or future multipart reflection.

### Activation

Default/disabled auth always rejects mutation. An explicitly validated local/demo composition may activate only contract validation and a safe local staging placeholder after owner approval. Production remains unavailable.

### Tests

Disabled default, unauthenticated, permission/tenant/service-account denial, malformed metadata, size enforcement, safe envelope, no body/path leakage, tenant-scoped reads, no runtime/export/ERP invocation, and unchanged existing GET routes.

### Stop Condition

No ingestion or Document State mutation unless separately approved for Phase 3.

## 4. Phase 3: Ingestion And Document State Writer Integration

**Status:** Complete at the safe intent/adapter-port boundary. Deterministic activation, opaque staged-artifact binding, safe ingestion and received-document intents, fixed receipts/results, and test-fake orchestration are implemented. Concrete staging, path resolution, ingestion execution, and existing writer/lifecycle adapters remain deferred because no trusted artifact source exists.

### Deliverables

- Private staging port/adapter suitable for tests and explicit local/demo mode; production storage unavailable.
- Producer-side adapter resolving an opaque reference and invoking the existing deterministic ingestion pipeline.
- Safe projection from ingestion results to existing ingestion/processing writer commands.
- Stable upload/document/source/workflow IDs and idempotent retry checkpoints.
- Governed `received` creation and `received -> ingested` lifecycle advancement.
- Safe failure/audit intents and cleanup ownership.

### Tests

Successful command creation, writer read-after-write, in-memory/SQLite composition compatibility without a new schema, lifecycle expected-version behavior, duplicate/replay, partial failure/resume, staging cleanup, raw-rich result projection rejection, no export trigger, and safe failure mapping.

### Stop Condition

No async queue, production blob storage, OCR/LLM, matching invention, export, or ERP.

## 5. Phase 4: Processing Status And Progress Read Models

**Status:** Complete. Immutable safe progress models, capability-aligned status/stage vocabularies, deterministic projection/query helpers, bounded tenant-scoped in-memory reads, and guarded upload/document progress API projections are implemented. They consume only safe facts and perform no mutation or processing activation.

### Deliverables

- Safe upload summaries and processing-status projection through existing Document State/Query Facade ownership.
- Tenant-scoped API GETs for upload collection/detail and document processing status if existing processing history is insufficient.
- Fixed stage/status vocabulary based only on actually recorded producer outputs.
- Deterministic ordering, pagination, timestamps, failure reason codes, and safe unavailable states.

### Tests

Tenant narrowing, concealed resources, deterministic ordering/pagination, read-after-write, partial/failed processing, safe codes, no raw content/path/metadata, and backend equivalence.

### Stop Condition

No new mutation or UI action.

## 6. Phase 5: FlowSync Upload UI And Processing Timeline

**Status:** Complete. FlowSync now provides a guarded `/uploads` experience that inspects browser-local metadata, explicitly submits JSON validation metadata only, treats staging-disabled as a governed preview result, reads recent uploads and API-supplied progress/timeline events, and adds a read-only document processing-status panel. Manual refresh, safe request states, responsive layout, and source checks prevent file-content transmission or unsupported processing claims.

### Deliverables

- Upload entry point gated by API capability/availability.
- Accessible picker/drag-drop, selected filename/type/size, safe validation feedback, and submit state.
- Recent uploads and processing timeline from API projections.
- Disabled/unavailable OCR, LLM, and export indicators.
- Preserve v0.17 visual identity and API-authority language.

### Rules

No client parsing/classification truth, tenant/permission decisions, raw content persistence, backend paths, optimistic processing success, export request, or ERP call. Do not enable the action until Phase 2/3 backend activation is explicitly approved and tested.

### Tests

Source validation, typecheck/build, accessibility states, disabled/unavailable and activated-local states, safe errors, no forbidden fields/storage, no processing-result construction, no export request, and existing route compilation.

### Stop Condition

No production enablement or closure without full verification.

## 7. Phase 6: Verification, Closure, Handoff, And Tag

**Status:** Complete pending owner tag. Summary, handoff, release notes, roadmap/debt/ADR/plan/changelog closure, verification evidence, deferred production-activation risks, and the v0.20 handoff recommendation are recorded. No implementation behavior changed during closure.

### Deliverables

- Summary, handoff, release notes, roadmap/debt/ADR/plan/changelog closure.
- Focused upload/API/security/Document State/lifecycle/Query Facade/FlowSync suites.
- Existing export, Streamlit, platform, and full regressions.
- Boundary/privacy checks and explicit production-unavailable statement.
- Recommended tag `v0.19-upload-processing-activation` after owner review.

## 8. Verification Matrix

Each phase should run relevant focused tests plus:

```text
python scripts/verify_boundaries.py
python -m pytest tests/api/document_intelligence -q
python -m pytest tests/platform_runtime -q
python -m pytest tests/security -q
python -m pytest tests/document_state -q
python -m pytest tests/workflow_runtime/query_facade tests/review_runtime -q
python -m pytest tests/export_runtime -q
python -m pytest tests/ui/streamlit -q

cd apps/flowsync-document-intelligence
npm run validate
npm run typecheck
npm run build
```

Full `python -m pytest -q` remains the closure target when practical.

## 9. Dependency And Migration Gates

Do not add a MIME library, malware scanner, queue, storage SDK, OCR/LLM client, or migration by convenience. Any new dependency or durable schema must include ownership, threat/dependency review, configuration, conformance tests, failure modes, operations, and explicit owner approval.

## 10. Recommended Commit Sequence

1. `feat(upload-runtime): add upload contracts and validation policy`
2. `feat(api): add guarded upload contracts`
3. `feat(upload): integrate deterministic ingestion and document state writers`
4. `feat(api): add safe upload processing projections`
5. `feat(flowsync): add guarded upload and processing views`
6. `docs: close v0.19 upload processing activation`
