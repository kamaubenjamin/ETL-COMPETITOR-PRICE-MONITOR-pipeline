# Upload-to-Processing Writer Integration v1 Implementation Plan

**Milestone:** v0.13
**Status:** Phase 1 complete; Phases 2-5 not started

## 1. Milestone Overview

v0.13 connects approved upload, ingestion, workflow, validation, matching, and review outcomes to existing Document State write ports. It introduces internal normalized commands and writer services, then verifies read-after-write visibility through the existing Query Facade and API provider chain.

Each phase is limited to one Codex session. No phase may proceed automatically. No public mutation endpoint, UI mutation, production database, raw blob store, auth/tenant implementation, OCR, LLM, external service, or competitor-price integration is included.

## 2. Phase 1: Writer Contracts And Mapping Definitions

### Objectives

- Create immutable JSON-compatible writer commands and bounded result/error contracts.
- Define opaque artifact references and privacy rejection rules.
- Define fixed lifecycle/stage/status mapping catalogs.
- Define deterministic ID, append-key, create-retry, and expected-version rules.
- Keep contracts independent of runtime implementations and repository engines.

### Expected Files

Create:

- `src/document_state/writers/__init__.py`
- `src/document_state/writers/commands.py`
- `src/document_state/writers/errors.py`
- `src/document_state/writers/idempotency.py`
- `src/document_state/writers/mappings.py`
- `src/document_state/writers/ports.py`
- `src/document_state/writers/results.py`
- `tests/document_state/writers/__init__.py`
- `tests/document_state/writers/test_commands.py`
- `tests/document_state/writers/test_idempotency.py`
- `tests/document_state/writers/test_mappings.py`
- `tests/document_state/writers/test_ports.py`
- `tests/document_state/writers/test_results.py`
- `tests/document_state/writers/test_boundaries.py`

Modify only if narrowly required:

- `src/document_state/privacy.py` to allow specific bounded opaque artifact-reference metadata keys.
- `src/document_state/__init__.py` for public writer command exports.
- v0.13 status documentation.

### Tests

- Commands are immutable and serialize to JSON-compatible dictionaries.
- IDs, timestamps, statuses, expected versions, collections, and metadata are bounded.
- Raw document, row, correction, artifact, stack-trace, path, credential, OCR, and LLM fields are rejected.
- Deterministic keys are stable under repeated construction and independent of mapping iteration order.
- Fixed stage/status mappings reject unknown values rather than guessing.
- Writer package has no runtime, API, UI, persistence-engine, storage, telemetry, network, or external dependency imports.

### Verification

```text
python -m pytest tests/document_state/writers -q
python -m pytest tests/document_state -q
python scripts/verify_boundaries.py
python -m py_compile src/document_state/writers/commands.py
python -m py_compile src/document_state/writers/mappings.py
python -m py_compile src/document_state/writers/idempotency.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after contracts, mappings, privacy rules, and focused verification. Do not implement repository writes or producer integration.

Phase 1 completed with immutable JSON-compatible commands, opaque artifact references, fixed safe errors/results, hashed domain-separated idempotency keys, deterministic mappings, structural writer ports, and boundary tests. No repository or producer integration was added.

## 3. Phase 2: Ingestion-To-Document-State Writer Service

### Objectives

- Implement the internal ingestion writer using injected Document State read/write ports.
- Create or safely compare initial document records.
- Append deterministic received/ingested/classified/parsed lifecycle and audit events.
- Create/update ingestion processing snapshots with explicit versions.
- Add a producer-side adapter for public Document Engine result contracts without serializing full documents.
- Preserve resumable, operation-level consistency under partial failure.

### Expected Files

Create:

- `src/document_state/writers/ingestion_writer.py`
- `src/document_engine/integrations/__init__.py`
- `src/document_engine/integrations/document_state.py`
- `tests/document_state/writers/test_ingestion_writer.py`
- `tests/document_engine/test_document_state_integration.py`

Modify only if an explicit injection seam is required:

- `src/document_engine/orchestration/ingestion_pipeline.py`
- `src/document_state/writers/__init__.py`
- v0.13 status documentation.

### Required Behavior

- Writer construction receives protocol ports explicitly; it never calls composition or selects a backend.
- Ingestion mapping consumes selected scalar fields from `DocumentIngestionResult`/`IngestionPipelineResult`, not wholesale `to_dict()` payloads.
- File paths are reduced to safe filenames; document and normalized content are excluded.
- Retry of identical create/event commands succeeds; conflicting content returns safe conflict.
- Writes occur in documented replay-safe order with committed-operation reporting.
- Both in-memory and SQLite compositions satisfy the same tests.

### Verification

```text
python -m pytest tests/document_state/writers/test_ingestion_writer.py tests/document_engine/test_document_state_integration.py -q
python -m pytest tests/document_state tests/document_engine -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after ingestion writer integration and verification. Do not add workflow, validation, matching, review, API, or UI writes.

## 4. Phase 3: Processing, Validation, Matching, And Review Writers

### Objectives

- Implement workflow run and processing snapshot writers.
- Implement validation issue and matching summary writers.
- Implement review reference, correction summary, reprocess plan, and audit writers.
- Add producer-side adapters for public Workflow and Review result contracts.
- Translate raw errors and metadata into fixed safe codes/templates.
- Preserve explicit versions and deterministic append identities.

### Expected Files

Create:

- `src/document_state/writers/processing_writer.py`
- `src/document_state/writers/review_writer.py`
- `src/workflow_runtime/integrations/__init__.py`
- `src/workflow_runtime/integrations/document_state.py`
- `src/review_runtime/integrations/__init__.py`
- `src/review_runtime/integrations/document_state.py`
- `tests/document_state/writers/test_processing_writer.py`
- `tests/document_state/writers/test_review_writer.py`
- `tests/workflow_runtime/test_document_state_integration.py`
- `tests/review_runtime/test_document_state_integration.py`

Modify only for explicit optional injection after current behavior is preserved:

- `src/workflow_runtime/runtime/workflow_runner.py`
- Review Runtime service composition modules.
- `src/document_state/writers/__init__.py`
- v0.13 status documentation.

### Required Behavior

- `WorkflowResult`/`StageResult` output artifacts are never persisted.
- Validation issues exclude rows and failed raw values.
- Matching summaries exclude request/master/candidate payloads.
- Corrections exclude old/new values.
- Reprocess plans persist stage names and counts, not artifact lists.
- Audit metadata remains scalar, bounded, and allowlisted.
- Failed state writes do not produce success audit events.
- Stale versions fail safely and are not silently retried.

### Verification

```text
python -m pytest tests/document_state/writers tests/workflow_runtime/test_document_state_integration.py tests/review_runtime/test_document_state_integration.py -q
python -m pytest tests/document_state tests/workflow_runtime/query_facade tests/review_runtime -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after processing/review writer services and verification. Do not add API endpoints, Streamlit actions, production activation, or cross-record transactions.

## 5. Phase 4: End-To-End Read-After-Write Verification

### Objectives

- Verify deterministic upload/ingestion through writer services into both backends.
- Verify workflow, validation, matching, review, correction, reprocess, and audit state in one read-after-write path.
- Read persisted state through `DocumentStateQueryFacadeAdapter` and existing API provider mappings.
- Confirm API envelopes, paths, methods, payload meanings, request IDs, and headers remain unchanged.
- Confirm Streamlit `api_preview` remains compatible and read-only.
- Harden recursive import/privacy checks.

### Expected Files

Create:

- `tests/document_state/writers/test_read_after_write_integration.py`
- `tests/document_state/writers/test_writer_privacy_integration.py`
- `tests/document_state/writers/test_writer_boundary_rules.py`
- `tests/api/document_intelligence/test_writer_read_after_write.py`

Modify only if verified defects require it:

- writer services or producer adapters.
- existing Query Facade/API tests.
- v0.13 status documentation.

### Tests

- Identical results for in-memory and SQLite backends.
- State survives SQLite composition reconstruction.
- Query Facade projections match repository state after writes.
- Existing API provider shapes expose the new state without endpoint changes.
- Partial failure followed by identical replay completes missing operations without duplicates.
- No raw source/document/row/correction/artifact/error data crosses the writer, repository, facade, or API boundaries.
- API/UI contain no writer or persistence imports and expose no mutation routes/actions.

### Verification

```text
python -m pytest tests/document_state -q
python -m pytest tests/workflow_runtime/query_facade -q
python -m pytest tests/api/document_intelligence tests/ui/streamlit tests/review_runtime -q
python scripts/verify_boundaries.py
python -m py_compile src/document_state/writers/ingestion_writer.py
python -m py_compile src/document_state/writers/processing_writer.py
git diff --check
git status --short --branch
```

### Stop Condition

Stop after read-after-write, privacy, compatibility, and boundary verification. Do not activate production mode or add mutation APIs/UI.

## 6. Phase 5: Documentation, Release Closure, And Handoff

### Objectives

- Run focused and full regression suites.
- Add architecture summary, handoff, release notes, and operations limitations.
- Update plans, ADR, roadmap, technical debt, and changelog accurately.
- Prepare but do not create the owner tag.

### Expected Files

Create:

- `docs/architecture/UPLOAD_PROCESSING_WRITER_INTEGRATION_V1_SUMMARY.md`
- `docs/architecture/UPLOAD_PROCESSING_WRITER_INTEGRATION_V1_HANDOFF.md`
- `docs/releases/v0.13-upload-processing-writer-integration.md`

Modify:

- both v0.13 plans.
- `docs/adr/ADR-018-upload-processing-writer-integration.md`.
- `docs/ROADMAP.md`.
- `TECHNICAL_DEBT.md`.
- `CHANGELOG.md`.

### Verification

```text
python -m pytest tests/document_state -q
python -m pytest tests/workflow_runtime/query_facade -q
python -m pytest tests/api/document_intelligence tests/ui/streamlit tests/review_runtime -q
python scripts/verify_boundaries.py
python -m pytest -q
git diff --check
git status --short --branch
```

### Stop Condition

Stop after documentation and verification. Do not commit, push, or tag unless explicitly instructed.

## 7. Boundary Requirements

- Document State writer services import only standard library and public/package-local Document State contracts.
- Producer adapters import only their own public result contracts and public writer commands.
- Writers depend on repository protocols, never SQLite/in-memory concrete classes.
- API, Streamlit, and Query Facade remain read-only and import no writers.
- Backend selection remains in `DocumentStateComposition`; producer adapters never select or fall back.
- No storage, telemetry internal, FlowSync, competitor-price, external-service, OCR, LLM, or database-driver imports are added to writer modules.

## 8. Backward Compatibility Requirements

- Preserve all v0.9 paths, GET-only methods, payload meanings, envelopes, pagination, request IDs, and security headers.
- Preserve v0.10 Query Facade contracts and v0.11/v0.12 repository interfaces.
- Preserve Streamlit `local_preview` and `api_preview` behavior.
- Writer injection is optional until an owner-approved application bootstrap activates it.
- Leave legacy `src/api/app.py`, root `dashboard.py`, and competitor-price modules untouched.

## 9. Risks And Mitigations

- **Partial multi-record writes:** deterministic prevalidation, ordered checkpoints, stable IDs, replay, and explicit committed-operation results.
- **Duplicate ingestion:** read-compare-create plus append idempotency; never convert arbitrary conflicts into success.
- **Lost updates:** caller-supplied expected versions and fail-closed compare-and-swap.
- **Unsafe runtime payloads:** normalized commands and producer-side projection; prohibit wholesale result serialization.
- **Lifecycle drift:** fixed mapping catalog with unknown-stage rejection.
- **Cross-runtime coupling:** producer adapters own runtime imports; Document State writers remain runtime-neutral.
- **Audit inconsistency:** append success audit only after corresponding state operation succeeds.
- **Production overstatement:** both backends are local/dev/test choices; production activation and PostgreSQL remain deferred.

## 10. Definition Of Done

- All ten Document State record families have an internal writer path.
- Ingestion and processing retries are deterministic and conflict-safe.
- Mutable snapshots use explicit compare-and-swap versions.
- Append-only records use deterministic idempotency identities.
- Privacy-safe opaque references replace raw artifacts/payloads.
- Both active backends pass shared writer and read-after-write tests.
- Existing Query Facade/API/Streamlit behavior remains compatible and read-only.
- Boundaries and full regression pass.
- Release summary, handoff, notes, roadmap, debt, changelog, and ADR are complete.

## 11. Commit And Tag Strategy

Recommended owner-reviewed commits:

1. `feat: add document state writer contracts`
2. `feat: add ingestion document state writer`
3. `feat: add processing and review state writers`
4. `test: verify writer read-after-write integration`
5. `chore: close v0.13 upload processing writer integration`

Recommended tag after Phase 5 owner verification:

`v0.13-upload-processing-writer-integration`
