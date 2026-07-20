# v0.21 Phase 6 API Runtime Dependency And Bundle Hotfix

## Scope And Outcome

The first Phase 6 hotfix added pandas after the hosted runtime proved that `api/index.py` imported it during startup. Vercel then installed pandas successfully but rejected the resulting 277.74 MB function bundle against the 225 MB build-path limit.

This follow-up removes the accidental tabular import from API startup and restores the three-package API manifest. It changes only package initialization and deployment validation. It does not change routes, Auth, Supabase, RLS, CORS, transformation semantics, runtime composition behavior, or production authority, and it performs no deployment.

## Root Cause

Importing `src.workflow_runtime.query_facade` first initializes the parent `src.workflow_runtime` package. Its package facade eagerly imported `WorkflowParser`, `WorkflowValidator`, `WorkflowRunner`, workspace services, and locking exports. The validator imported `src.workflow_runtime.operations.stage_catalog`; initializing the operations package then imported every stage, including `TransformStage`. That stage imported the pandas-based transformation pipeline, and initializing `src.transforms` eagerly imported aggregation and the rest of its pandas implementation.

The API needs only the Query Facade contracts during default startup. Health, Auth, session, and Workflow Studio route registration do not execute Workflow Runtime stages or transformations.

## Lazy Import Boundary

`src.workflow_runtime.__init__` retains its existing `__all__` public names but resolves each implementation through module-level `__getattr__` only when a caller requests that name. Resolved attributes are cached in the package globals, so explicit public imports retain normal Python import behavior after first access.

This is deliberately the earliest narrow boundary. It avoids changing `TransformStage`, the transforms package API, transformation implementations, operation registration, stage execution, or runtime composition. Explicit imports such as `from src.workflow_runtime import WorkflowRunner` still load the implementation. Explicit transformation imports and operations continue to load pandas in the full local runtime where pandas is installed.

## Deployment Dependency Decision

`requirements-api.txt` again contains only:

```text
fastapi==0.139.2
httpx==0.28.1
PyJWT[crypto]==2.10.1
```

Pandas and NumPy are prohibited from the Vercel API manifest and from the `api.index` startup module set. They remain in the root development/runtime dependency manifest for actual transformation execution.

## Clean Python 3.12 Verification

A new Python 3.12 virtual environment installed only `requirements-api.txt`. In that environment:

```text
from api.index import app
assert "pandas" not in sys.modules
assert "numpy" not in sys.modules
```

The import printed `FastAPI`, `pip check` reported no broken requirements, and route inspection retained `/health`, `/api/v1/health`, `/api/v1/workflow-definitions`, and the complete existing API path set. The import validator also denied network and persistent filesystem-write attempts during startup.

## Regression Guard

`scripts/validate_api_runtime_dependencies.py` now verifies:

- the exact three direct deployment dependencies;
- pandas, NumPy, and unrelated heavy packages are absent from the manifest;
- neither `pandas` nor `numpy` appears in `sys.modules` after `api.index` import;
- the exported object remains FastAPI;
- health and Workflow Studio routes remain registered;
- import requires no network or persistent filesystem write.

The entrypoint tests run the validator in a subprocess, independently assert the clean module set and required routes, and explicitly execute grouped transformation behavior through the existing public `src.transforms` API.

## Estimated Deployment Impact

The repository's current Windows Python 3.12 installation attributes approximately 61.13 MiB to pandas, 50.41 MiB to NumPy, and 1.36 MiB to their date/time helper distributions, for an approximate 112.90 MiB installed reduction. Applying that local estimate to the rejected 277.74 MB bundle suggests roughly 164.84 MB, about 60.16 MB below the 225 MB limit.

This is an estimate only. Vercel uses Linux wheels and its own bundling/compression accounting, so an owner-authorized redeployment is still required to confirm the hosted artifact size.

## Deployment Boundary And Remaining Risk

No Vercel redeployment was performed. The owner must deploy the reviewed commit separately, confirm the reported function size, then recheck health, docs, session/Auth, CORS, and Workflow Studio routes.

The lazy facade preserves supported named exports, but code that depended only on the side effect of `import src.workflow_runtime` eagerly registering every executable stage must instead import `src.workflow_runtime.operations`, as the existing runtime integration tests already do. Transformation execution still requires the root/full runtime dependencies and is not available inside the intentionally minimal hosted API function.

Synthetic, non-confidential UAT data remains mandatory. Hosted state remains ephemeral and all existing Phase 5/6 Auth, free-tier, and operational limitations remain in force.

## Verification Record

Completed locally on Python 3.12.13:

- clean manifest-only install, exact no-pandas/no-NumPy import command, route inspection, validator, and `pip check`: passed;
- targeted lazy-loading, serverless, Workflow Runtime, and transformation selection: 205 passed;
- Document Intelligence API: 182 passed with one upstream TestClient deprecation warning;
- Workflow Studio: 180 passed;
- Security: 69 passed;
- Tier 1 runtime boundaries: `COMPLIANT`, retaining two pre-existing BOM parse warnings;
- high-signal secret scan, prohibited dependency scan, and diff hygiene: passed.

The disposable validation environment was removed after verification. No deployment, commit, push, or tag was performed.
