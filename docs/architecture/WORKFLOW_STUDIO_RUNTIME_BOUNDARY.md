# Workflow Studio Runtime Boundary

## Final v0.20 Flow

```text
FlowSync Rules Studio
  -> Guarded Workflow Management API
  -> API-owned tenant and actor authority
  -> Workflow Studio provider
  -> Workflow definition/version repository
  -> Validation engine
  -> Draft lifecycle/versioning
  -> Preview boundary
  -> Approval/publication policy
  -> Immutable governed publication
```

This is a governance flow, not an execution flow. Existing Workflow Runtime remains the sole authority for runtime DSL validation, dependency resolution, DAG construction, registered operations, locking, scheduling composition, and execution. Workflow Studio does not import or replace a runtime implementation.

## Repository And Lifecycle Boundary

Workflow definitions, versions, publications, and audit intents use persistence-neutral contracts backed in v0.20 by a process-local in-memory store. Optimistic revisions protect same-process updates; they are not distributed locks or transactions.

```text
draft -> validated -> test_passed -> approved -> published
                                           \-> superseded / inactive -> archived
```

Only drafts are editable. Published history is immutable. Rollback creates a derived new draft/version and repeats validation, testing, approval, and publication. Publishing a newer version may supersede the previous active publication. Deactivation does not select or activate a fallback. Archive preserves records; no hard deletion is exposed.

## Preview Boundary

Preview accepts only an approved safe fixture reference or a bounded privacy-checked inline sample. Validation and eligibility gates run before the injected `WorkflowPreviewPort`. The default composition may return `preview_unavailable`; no Workflow Runtime implementation is currently connected.

Preview performs no production data mutation and cannot write Document State, workflow lifecycle, export, ERP, alerts, master data, upload staging, files, databases, or networks. Results are re-bounded and redacted; raw exceptions, unrestricted outputs, payload bodies, credentials, tokens, claims, paths, and protected values are not exposed. Timeout and cancellation are descriptors only because v0.20 has no isolated worker or enforced process cancellation.

## Publication Boundary

**Published definition governance only; production execution activation is not enabled.**

Publication records an approved immutable definition and may supersede the previous active governed publication. It does not compile into or bind the Workflow Runtime, register an operation, attach a schedule or event, promote an environment, or activate execution. A real preview/runtime adapter, UAT promotion policy, production promotion policy, runtime binding, and scheduler integration remain deferred tracks requiring separate review.

## Interface Authority

The API and UI do not bypass policy boundaries. The API composes trusted tenant/actor context and applies authorization, validation, lifecycle, preview, and publication services. FlowSync is a typed client only; it never accesses the repository, runtime registry, or execution engine directly.

