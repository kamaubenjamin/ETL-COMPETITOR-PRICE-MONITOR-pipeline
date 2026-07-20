# v0.20 Business Workflow / Rules Studio Implementation Summary

## Delivered Architecture

v0.20 adds a governance layer above the existing Workflow Runtime. It does not replace or extend the runtime executor.

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

The API and UI consume the same policy-controlled services and do not access repositories or execution implementations directly. Repository state is currently in-memory and process-local.

## Delivered Capabilities

- Workflow, rule, condition, action, version, publication, validation, preview, and audit contracts.
- A stable operation catalog with explicit availability, preview, and publication eligibility.
- Deterministic structural, dependency, cycle, logical-path, condition, action, runtime-compatibility, and publication-readiness validation.
- Report-only legacy Sanifu/Docsift compatibility classification with bounded lineage and no executable conversion.
- Persistence-neutral repository interfaces and a lock-protected in-memory implementation.
- Draft lifecycle, optimistic revisions, immutable history, approval/publication policy, supersession, deactivation, archive, and rollback-as-new-draft behavior.
- Safe fixture and bounded inline-sample preview requests, fixed limits, injected runtime port, placeholder adapters, safe trace/audit intents, bounded projections, and redaction.
- Guarded Workflow Management API routes with tenant concealment, API-owned attribution, strict payloads, safe errors, and management-specific permissions.
- FlowSync definition list/create/detail, version and audit history, structured rule/dependency/condition/action editing, catalog-backed operation selection, validation, preview, and lifecycle controls.

## Governed Lifecycle

```text
draft -> validated -> test_passed -> approved -> published
                                           \-> superseded / inactive -> archived
```

- Only drafts are editable.
- Approved and published history is immutable.
- Rollback clones an earlier immutable version into a new draft/version; it never rewrites history.
- A new publication may supersede the prior active publication.
- Deactivation makes the active publication inactive and does not auto-activate another version.
- Archive preserves history; there is no hard-delete path.

## Publication Meaning

**Published definition governance only; production execution activation is not enabled.**

Publication persists an immutable governed definition in the current process-local store and may supersede a previous active publication. Runtime binding, scheduler/event integration, UAT promotion, production promotion, and activation policy remain separate future work.

## Current Limits

The store is non-durable; there are no database migrations, distributed transactions, or distributed locks. The default preview may return `preview_unavailable`; no Workflow Runtime implementation is connected. Timeout and cancellation are policy descriptors, not enforced worker controls. The operation catalog is deliberately conservative, and unsupported legacy semantics remain unavailable or require manual review.

