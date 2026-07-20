# v0.21 Phase 6 API Runtime Dependency Hotfix

## Scope And Outcome

This narrow hotfix repairs the Vercel Project B Python dependency manifest after the hosted runtime reached `api/index.py` and failed with `ModuleNotFoundError: No module named 'pandas'`. It changes packaging verification only. It does not change the Supabase schema, Auth, CORS, application routes, runtime behavior, deployment configuration, or production authority, and it performs no deployment.

## Root Cause

`api/index.py` re-exports `src.api.document_intelligence.app:app`. Application startup imports API Auth composition, which imports `src.platform_runtime`. Platform Runtime imports Workflow Runtime contracts and operations. `TransformStage` imports `src.transforms.contracts`; Python first initializes `src.transforms`, whose eager public exports import `src.transforms.aggregation`, and that module imports pandas.

The Phase 3 manifest was validated against top-level API framework imports rather than by installing only that manifest and importing the deployment entrypoint in a clean environment. It therefore omitted a real startup dependency even though the default app does not execute a transformation during startup.

## Dependency Decision

The API-only manifest adds exactly:

```text
pandas==3.0.2
```

This is the exact version already proven in the repository's Python 3.12.13 environment and in the root manifest. A clean resolver supplies NumPy, python-dateutil, and tzdata as pandas dependencies; they are deliberately not duplicated in `requirements-api.txt`.

After pandas was installed, the clean `api.index` import succeeded without another missing package. Streamlit, Selenium, Playwright, pytest, browser automation, OCR/LLM packages, report tooling, unrelated ETL connectors, and `uvicorn` remain excluded.

## Clean Import Procedure

The validation used a new Python 3.12 virtual environment under the system temporary directory:

```text
python -m venv <temporary-environment>
<temporary-python> -m pip install -r requirements-api.txt
<temporary-python> -c "from api.index import app; print(type(app).__name__)"
<temporary-python> scripts/validate_api_runtime_dependencies.py
```

The final entrypoint command printed `FastAPI`. Route inspection retained `/health`, `/api/v1/health`, documentation routes, and all existing application routes.

## Regression Guard

`scripts/validate_api_runtime_dependencies.py` is standard-library-only until it performs the deployment import. It verifies the exact direct API manifest, rejects prohibited unrelated packages, disables bytecode writes, refuses network and filesystem-write attempts during import, confirms the exported object is FastAPI, and confirms both health routes remain registered.

`tests/api/document_intelligence/test_vercel_entrypoint.py` now enforces the corrected manifest and runs this validator with the active test interpreter. For the deployment gate, the same validator must also run after installing only `requirements-api.txt` in a clean Python 3.12 environment.

## Deployment Boundary And Remaining Risk

This fix does not deploy or redeploy either Vercel project. The owner must redeploy Project B separately after reviewing the change, then recheck `/health`, `/api/v1/health`, `/docs`, and the hosted Auth/CORS flow.

The eager package import makes pandas part of cold-start memory and bundle size even when transformation execution is not composed. Removing that cost would require a separately reviewed runtime/package import refactor and is outside this hotfix. Hosted state remains ephemeral, synthetic non-confidential UAT data remains mandatory, and all Phase 5/6 Auth, free-tier, and operational limitations remain in force.

## Verification Record

Completed locally on Python 3.12.13:

- a new virtual environment installed only `requirements-api.txt` and `pip check` reported no broken requirements;
- `from api.index import app` printed `FastAPI` before and after a fresh manifest install;
- the dependency/no-I/O validator passed in the clean environment and confirmed `/health` plus `/api/v1/health`;
- Document Intelligence API: 179 passed with one upstream TestClient deprecation warning;
- Workflow Studio: 180 passed;
- Security: 69 passed;
- Tier 1 runtime boundaries: `COMPLIANT`, with the two pre-existing BOM parse warnings;
- high-signal tracked-repository and changed-file secret scans: passed;
- prohibited manifest package scan and `git diff --check`: passed.

The two disposable validation environments were removed after verification. No deployment, commit, push, or tag was performed.
