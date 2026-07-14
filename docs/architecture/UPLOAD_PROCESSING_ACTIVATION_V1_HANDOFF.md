# Upload + Processing Activation v1 Handoff

## Current State

v0.19 is implemented, verified, and closed pending owner tag. Treat the upload POST as a guarded metadata-validation preview and the progress surfaces as safe read projections. Raw-file transfer, staging, ingestion execution, and durable upload progress do not exist in this release.

## Safe Starting Points

- Upload policy and contracts: `src/upload_runtime/`
- Guarded API routes: `src/api/document_intelligence/routers/uploads.py`
- App-scoped safe provider: `src/api/document_intelligence/providers/upload_provider.py`
- FlowSync upload client: `apps/flowsync-document-intelligence/src/api/uploads.ts`
- FlowSync upload page: `apps/flowsync-document-intelligence/src/pages/UploadsPage.tsx`
- Architecture decision: `docs/adr/ADR-024-upload-processing-activation-boundary.md`
- Closure summary: `docs/architecture/UPLOAD_PROCESSING_ACTIVATION_V1_SUMMARY.md`

## Invariants To Preserve

- Keep `upload_runtime` standard-library/package-local only.
- Keep identity, tenant scope, permission, validation outcome, and visibility API-authoritative.
- Never accept UI-supplied tenant or actor identity.
- Require a validated command and matching opaque artifact reference before activation ports can be called.
- Never expose or serialize raw bytes/content, file/backend paths, credentials, tokens, claims, exceptions, or unrestricted metadata.
- Never fabricate processing stages, events, completion, or percentages.
- Keep the UI action named **Validate upload** until actual staging and processing are approved and observable.
- Keep upload paths isolated from export, ERP, OCR, and LLM behavior.

## Production Activation Prerequisites

Do not enable upload processing with a feature flag alone. Production readiness requires a trusted staging adapter, approved private durable storage, multipart/raw transport controls, malware scanning/quarantine, retention/deletion/legal-hold policy, a real ingestion adapter, durable upload/progress persistence, async timeout ownership, queue/outbox/workers, retry/reconciliation, production authentication, operational telemetry/runbooks, and live end-to-end security/conformance testing.

## Known Risks And Open Questions

- Production storage selection, encryption, retention, deletion, and recovery are undecided.
- Existing ingestion remains path-oriented and needs a private artifact resolver.
- Synchronous execution may exceed HTTP request timeouts.
- MIME/signature validation remains intentionally limited without an approved dependency.
- XLSX decompression/resource limits and EML attachment/header policies remain unresolved.
- Upload/progress state is app-scoped and in-memory.
- Staging and real processing remain disabled.
- Desktop/mobile rendered browser verification remains outstanding.
- Retry semantics, partial failure reconciliation, and intentional duplicate re-upload policy need owner decisions.

## Recommended Next Milestone

Proceed with **v0.20 Business Workflow / Rules Studio planning**. Maintain upload staging and ingestion activation as a visible production-readiness track with its own security, storage, operations, and verification gates. Do not absorb it implicitly into workflow-studio implementation.

## Verification Commands

```text
python scripts/verify_boundaries.py

cd apps/flowsync-document-intelligence
npm run validate
npm run typecheck
npm run build

git diff --check
git status --short --branch
```

The implementation regression baseline is 1,777 passed and 9 skipped. Re-run focused or full Python suites when future work changes source or tests; documentation-only closure does not require repeating that baseline.

