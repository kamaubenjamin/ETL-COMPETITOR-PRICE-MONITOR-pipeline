# v0.20 Business Workflow / Rules Studio

## Release Status

Implemented and closed pending owner commit and tag.

## Highlights

- Governed immutable workflow, rule, condition, action, version, publication, validation, preview, and audit contracts.
- Deterministic operation-catalog, dependency, cycle, path, compatibility, and publication validation.
- Safe non-executable legacy Sanifu/Docsift compatibility reporting.
- Process-local version repository, optimistic concurrency, controlled draft/test/approval/publication lifecycle, immutable published history, and safe audit intents.
- Bounded fixture/inline preview boundary with placeholder adapters, redacted outputs, and no production side effects.
- Tenant-scoped guarded Workflow Management API with distinct permissions and API-owned identity.
- FlowSync structured authoring, validation, preview, version/audit history, and publication-governance interface.

## API Inventory

Read routes:

- `GET /api/v1/workflow-definitions`
- `GET /api/v1/workflow-definitions/{workflow_id}`
- `GET /api/v1/workflow-definitions/{workflow_id}/versions`
- `GET /api/v1/workflow-definitions/{workflow_id}/versions/{version_id}`
- `GET /api/v1/workflow-definitions/{workflow_id}/audit`
- `GET /api/v1/workflow-operations`

Mutation routes:

- `POST /api/v1/workflow-definitions`
- `POST /api/v1/workflow-definitions/{workflow_id}/versions`
- `PATCH /api/v1/workflow-definitions/{workflow_id}/versions/{version_id}`
- `POST /api/v1/workflow-definitions/{workflow_id}/versions/{version_id}/validate`
- `POST /api/v1/workflow-definitions/{workflow_id}/versions/{version_id}/test`
- `POST /api/v1/workflow-definitions/{workflow_id}/versions/{version_id}/submit`
- `POST /api/v1/workflow-definitions/{workflow_id}/versions/{version_id}/approve`
- `POST /api/v1/workflow-definitions/{workflow_id}/versions/{version_id}/publish`
- `POST /api/v1/workflow-definitions/{workflow_id}/deactivate`
- `POST /api/v1/workflow-definitions/{workflow_id}/archive`

## FlowSync Inventory

Routes:

- `/workflows`
- `/workflows/new`
- `/workflows/:workflowId`
- `/workflows/:workflowId/versions/:versionId/edit`

The UI can list and create workflows; inspect definitions, versions, catalog entries, and audit history; author structured rules, dependencies, conditions, and actions; render validation; request bounded previews; and expose submit, approve, publish, deactivate, and archive controls according to non-authoritative permission hints.

## Security

The fixed catalog is `workflow:read`, `workflow:run`, `workflow:create`, `workflow:edit`, `workflow:test`, `workflow:approve`, `workflow:publish`, `workflow:deactivate`, and `workflow:admin`. Viewer receives read; reviewer receives no Workflow Studio management rights; operations manager receives create/edit/test/approve/deactivate; tenant admin additionally receives publish/admin; platform admin receives the full catalog; service account receives no Studio management rights. `workflow:read` and `workflow:run` do not imply management authority.

## Compatibility And Boundaries

Existing Workflow Runtime and existing FlowSync runtime activity remain intact. **Published definition governance only; production execution activation is not enabled.** No database migration, dependency, production adapter, ERP/export connection, staging, OCR/LLM, competitor-price, or Streamlit/dashboard behavior changed.

## Known Limitations

- Repositories and audit state are in-memory and process-local; there is no durable Workflow Studio persistence, database schema, migration, distributed locking, or transaction boundary.
- No real Workflow Runtime preview adapter, isolated worker, production activation, or UAT/environment promotion model exists.
- Timeout and cancellation are non-enforced descriptors.
- Permission discovery is a build-time hint; the API remains authoritative.
- Trusted validation, test, approval, permission, and feature facts rely on outer composition.
- Active publication revision exposure remains limited.
- The operation catalog remains conservative; many legacy operations are unavailable or manual-review-only.
- Regex/compiler semantic equivalence and executable legacy conversion remain deferred.
- FlowSync has no component-test framework and linting is not configured.
- Boundary verification retains two unrelated pre-existing U+FEFF warnings.

## Verification

- Workflow Studio: 180 passed.
- Document Intelligence API: 118 passed, 9 skipped.
- Security: 60 passed.
- Workflow Runtime: 64 passed.
- Upload Runtime: 78 passed.
- Export Runtime: 133 passed.
- Platform Runtime: 84 passed.
- Document State: 330 passed.
- Query Facade and Review Runtime: 239 passed.
- Streamlit UI: 64 passed.
- Full regression: 1,964 passed, 9 skipped.
- FlowSync source validation (74 files), typecheck, production build, lint command, and dedicated Studio validator: passed. The lint command reports that linting is not configured.
- Runtime boundary verification: compliant with the two known BOM warnings.
- `git diff --check`: passed with line-ending conversion warnings only.

## Recommended Tag

`v0.20-business-workflow-rules-studio`
