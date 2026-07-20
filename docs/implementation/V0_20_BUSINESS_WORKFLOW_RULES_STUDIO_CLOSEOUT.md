# v0.20 Business Workflow / Rules Studio Closeout

## Status

v0.20 is implemented and closed pending owner commit and tag. Phase 7 changes documentation only; it adds no product behavior, API route, migration, dependency, adapter, or production activation.

## Milestone Result

The milestone delivered:

- Immutable Workflow Studio domain contracts for workflows, rules, conditions, actions, versions, publications, validation, preview, and safe audit intents.
- A conservative operation catalog and deterministic validation engine covering dependencies, cycles, logical paths, operation compatibility, publication readiness, and non-executable Sanifu/Docsift compatibility reporting.
- Versioned repository contracts, a process-local in-memory store, optimistic concurrency, editable drafts, immutable published history, rollback-as-new-draft, publication policy, supersession, deactivation, and archive behavior.
- Safe fixture and bounded-inline-sample preview contracts, an injected preview runtime port, placeholder no-I/O adapters, bounded rule/stage projections, redacted outputs, and fixed failure results.
- A guarded tenant-scoped Workflow Management API with API-owned authority, distinct permissions, safe projections, and concealed cross-tenant resources.
- FlowSync Workflow Studio routes for definition management, structured authoring, catalog selection, validation, preview, lifecycle operations, version history, and audit history.

## Governing Boundary

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

Existing Workflow Runtime remains execution authority. **Published definition governance only; production execution activation is not enabled.** No real runtime preview adapter, scheduler binding, environment promotion, ERP/export integration, or production workflow activation is part of v0.20.

## Release Readiness Checklist

- [x] Architecture documentation complete
- [x] Implementation and handoff documentation complete
- [x] ADR-025 updated
- [x] Roadmap, technical debt, and changelog updated
- [x] API and FlowSync inventories documented
- [x] Security, tenancy, preview, lifecycle, and publication boundaries documented
- [x] Required focused and full regression commands pass in the final closure worktree
- [x] FlowSync validate, typecheck, production build, lint command, and dedicated validator pass
- [x] Boundary verifier and `git diff --check` pass
- [ ] Branch is clean before tag
- [x] No generated files intended for commit
- [x] No secrets added
- [x] No dependencies added
- [x] No production execution activation added

The only unchecked item is intentionally an owner gate: a dirty worktree containing only reviewed closure documentation is expected during this no-commit task. The owner must review and commit or otherwise clear it before tagging.

## Verification Evidence

| Check | Result |
|---|---|
| Workflow Studio | 180 passed |
| Document Intelligence API | 118 passed, 9 skipped |
| Security | 60 passed |
| Workflow Runtime | 64 passed |
| Upload Runtime | 78 passed |
| Export Runtime | 133 passed |
| Platform Runtime | 84 passed |
| Document State | 330 passed |
| Query Facade and Review Runtime | 239 passed |
| Streamlit UI | 64 passed |
| Full repository regression | 1,964 passed, 9 skipped |
| FlowSync source validation | Passed, 74 source files |
| FlowSync typecheck | Passed |
| FlowSync production build | Passed |
| FlowSync lint command | Passed; reports that linting is not configured |
| Dedicated Workflow Studio validator | Passed |
| Runtime boundary verifier | Compliant; two pre-existing U+FEFF skip warnings |
| `git diff --check` | Passed; line-ending conversion warnings only |

The shell-default `python` installation did not contain `pytest`; verification used the repository's available Codex Python runtime. Full regression rewrote four tracked demo-state files, which were restored to the committed baseline so they are not part of closure.

## Tag Readiness

When all verification items pass and the owner has reviewed and committed these documentation-only changes, the exact recommended tag is:

`v0.20-business-workflow-rules-studio`

Do not create the tag from the Phase 7 closure task.
