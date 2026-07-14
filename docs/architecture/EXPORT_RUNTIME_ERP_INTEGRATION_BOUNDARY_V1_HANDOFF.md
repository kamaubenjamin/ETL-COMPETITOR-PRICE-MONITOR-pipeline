# Export Runtime / ERP Integration Boundary v1 Handoff

## Current State

v0.18 is implemented, verified, and closed pending owner tag. Treat the export API and FlowSync surface as a contract preview only: history is read-only, mutation is disabled, adapters are placeholders, and no production delivery exists.

## Safe Starting Points

- Core contracts and orchestration: `src/export_runtime/`
- Disabled API boundary: `src/api/document_intelligence/routers/exports.py`
- Safe summary provider: `src/api/document_intelligence/providers/export_provider.py`
- FlowSync placeholder: `apps/flowsync-document-intelligence/src/components/ExportReadinessPanel.tsx`
- Architecture decision: `docs/adr/ADR-023-export-runtime-erp-integration-boundary.md`

## Invariants To Preserve

- Keep `export_runtime` standard-library/package-local only.
- Readiness, tenant authorization, and permission facts must be trusted before payload construction.
- Claim idempotency before adapter invocation; never silently redeliver an unknown outcome.
- Persist confirmed success before recommending lifecycle advancement.
- Never let API/UI call repositories, adapters, or ERP services directly.
- Keep credentials, vendor payloads/responses, raw documents/rows, claims, paths, exceptions, and unrestricted metadata out of public contracts.
- Keep current POST routes disabled until production prerequisites receive explicit owner approval.

## Activation Prerequisites

Do not enable export by merely adding a feature flag. Production activation requires authenticated identity, exact tenant/resource `document:export` authorization, durable attempt/result persistence, transactional delivery/outbox design, adapter ownership, credential resolution, timeout and unknown-outcome policy, retry/reconciliation workers, audit writer, lifecycle writer, operational controls, and end-to-end conformance/security tests.

## Known Risks And Open Questions

- External success followed by local persistence failure creates an unknown-delivery state.
- Durable export state is required before any production activation.
- Real ERP schemas and mapping ownership are unknown.
- Credential storage and rotation are not designed.
- Retry and reconciliation policies remain deferred.
- Export authorization activation remains deferred.
- FlowSync export presentation is placeholder/disabled only.

## Recommended Next Milestone

Proceed with **v0.19 Upload + Processing Activation**. Keep export mutation out of that milestone unless its production prerequisites become a separately approved scope. An eventual export-activation milestone should begin with persistence/outbox and security composition, not UI enablement or a real vendor call.

## Verification Commands

```text
python scripts/verify_boundaries.py
python -m pytest tests/export_runtime -q
python -m pytest tests/api/document_intelligence -q
python -m pytest tests/platform_runtime -q
python -m pytest tests/security -q
python -m pytest tests/document_state -q
python -m pytest tests/workflow_runtime/query_facade tests/review_runtime -q
python -m pytest tests/ui/streamlit -q

cd apps/flowsync-document-intelligence
npm run validate
npm run typecheck
npm run build
```

