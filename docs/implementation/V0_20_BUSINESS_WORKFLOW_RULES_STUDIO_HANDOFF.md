# v0.20 Business Workflow / Rules Studio Handoff

## Current State

v0.20 is a complete governance and authoring foundation pending owner commit and tag. It stores state only in the API process, exposes no production runtime activation, and uses no real Workflow Runtime preview adapter.

## Safe Starting Points

- Core contracts and policy: `src/workflow_studio/`
- Guarded API router: `src/api/document_intelligence/routers/workflow_studio.py`
- App-scoped provider: `src/api/document_intelligence/providers/workflow_studio_provider.py`
- Permission catalog and roles: `src/security/permissions.py`, `src/security/roles.py`
- FlowSync API service and types: `apps/flowsync-document-intelligence/src/services/workflowStudioApi.ts`, `apps/flowsync-document-intelligence/src/types/workflowStudio.ts`
- FlowSync pages: `apps/flowsync-document-intelligence/src/pages/WorkflowStudioPage.tsx`, `WorkflowDetailPage.tsx`, and `WorkflowEditorPage.tsx`
- Governing ADR: `docs/adr/ADR-025-business-workflow-rules-studio-boundary.md`
- Runtime and security summaries: `docs/architecture/WORKFLOW_STUDIO_RUNTIME_BOUNDARY.md` and `WORKFLOW_STUDIO_SECURITY_AND_GOVERNANCE_SUMMARY.md`

## Invariants To Preserve

- Existing Workflow Runtime remains the only execution authority.
- Keep authoring/governance separate from runtime parsing, DAG construction, scheduling, and execution.
- Keep tenant and actor identity API-owned; reject client-supplied authority.
- Conceal cross-tenant resources and enforce permissions server-side.
- Treat UI permission discovery only as a usability hint.
- Keep drafts as the only editable versions and published history immutable.
- Implement rollback as a new draft/version and preserve archive history.
- Keep preview bounded, redacted, side-effect free, and unavailable unless a reviewed adapter is injected.
- Never let preview mutate Document State, master data, export, ERP, alerts, staging, or production data.
- Keep publication distinct from production execution activation.
- Do not broaden catalog recognition into execution or publication eligibility.

## Next Engineering Track

Before durable or production use, owners must separately approve a tenant-aware durable repository and schema, transactional publication, durable audit, active-publication revision projection, capability discovery, isolated preview workers with enforced timeout/cancellation, a real reviewed runtime adapter, runtime compiler/binding, scheduler integration, and UAT/production promotion and activation policies.

Legacy migration additionally needs semantic conversion policy, operation equivalence proof, broader fixtures, and explicit tooling. Do not execute source legacy definitions or silently convert unsupported semantics.

## Operational Handoff

The default composition is suitable for contract validation and UI/API governance demonstrations only. Restarting the API loses Workflow Studio definitions, versions, publication records, and audit intents. A `published` response must not be interpreted as a live scheduled or event-bound workflow.

Use the verification matrix in `V0_20_BUSINESS_WORKFLOW_RULES_STUDIO_CLOSEOUT.md` before the owner commit/tag. The worktree must be clean before creating `v0.20-business-workflow-rules-studio`.

