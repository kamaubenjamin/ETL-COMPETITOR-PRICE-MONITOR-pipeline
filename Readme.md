# Data Automation and Intelligence Platform

An umbrella engineering repository for separate data-engineering and data-intelligence tracks that evolved from a reusable ETL foundation. The repository is currently named `ETL-COMPETITOR-PRICE-MONITOR-pipeline`; **Data Automation and Intelligence Platform** is the recommended descriptive name.

> **Product-boundary notice:** this is not one unified production application. The ETL foundation, Competitor Price Intelligence prototype, workflow runtime, and Intelligent Document Processing (IDP) platform live at different branch tips and have different entities, interfaces, maturity, and deployment boundaries. Branch-only code must not be assumed to exist on `main`.

## Current status

- **Default branch (`main`):** legacy/learning ETL foundation retained as the repository root.
- **Competitor Price Intelligence:** implemented prototype on `feature/parser-v2`; not production-ready and not fully verified against live sources.
- **Workflow Runtime:** stable retained-reference foundation on `workflow-runtime-stable`; its history continues in the IDP branch.
- **Intelligent Document Processing:** active technical-preview track on `platform/intelligent-document-processing`. The verified branch tip and tag close v0.22; v0.22.1 is the documented next milestone, not completed work.
- **Repository rename:** deferred. Vercel documentation and validation code explicitly reference the current repository name, and GitHub records active deployments. GitHub normally redirects an old repository URL after a rename, but Vercel project bindings, deploy hooks, local remotes, badges, and documentation must still be checked and updated.

## Branch-to-product map

| Branch | Purpose | Current status | Authoritative product track | Classification |
| --- | --- | --- | --- | --- |
| `main` | Generic extraction, dataframe transformation, CSV/SQLite loading, logging, and Streamlit control foundations; default example uses archived largest-bank data | Implemented foundation; legacy/learning state | ETL Pipeline Foundation | Retained reference (default) |
| `feature/parser-v2` | Multi-source product extraction, normalization, fuzzy matching, price comparison/history, alerts, workflows, and dashboard work | Implemented prototype; partially verified; known matching-quality limitations | Competitor Price Intelligence | Experimental |
| `workflow-runtime-stable` | Workflow contracts, definitions/DSL, validation, DAG construction, execution operations, telemetry, audit, API, and FlowSync integration foundations | Implemented stable baseline; superseded for current repository behavior by its IDP descendant | Workflow Runtime | Stable retained reference |
| `platform/intelligent-document-processing` | Tenant-scoped document APIs and read-only React interface, deterministic ingestion/parsing foundations, authentication, workflow rules, and purchase-order UAT demonstration | v0.22 completed technical preview; next milestone is planned v0.22.1 accuracy baseline | Intelligent Document Processing | Active |

The branch tips are intentionally divergent. Do not merge them merely to consolidate documentation.

## Project tracks

### ETL Pipeline Foundation

`main` contains reusable patterns for:

- extraction from web, files, dataframes, and connector abstractions;
- configurable dataframe cleaning, transformation, normalization, validation, and analysis;
- CSV and SQLite loading;
- pipeline state, logging, orchestration, and a Streamlit control surface;
- basic automated tests around extraction and orchestration.

The checked-in configuration and sample outputs still reflect an archived Wikipedia largest-banks exercise. They demonstrate the foundation; they are not evidence of a banking platform or live bank integration.

### Competitor Price Intelligence

`feature/parser-v2` is a separate prototype track. Repository evidence includes product extraction from multiple source types, normalization, RapidFuzz-based matching, comparison, price history/change handling, alerts, workflow helpers, reports, and a Streamlit dashboard.

This branch is **not** authoritative for `main`, and it is not production-ready. Legacy banking configuration remains, no CI result proves all tests against current live sources, and tracked output shows matching-quality defects that require further validation.

### Workflow Runtime

`workflow-runtime-stable` provides reusable workflow foundations: typed contracts, stored definitions and a DSL, validation, DAG construction, execution operations, telemetry/audit records, API surfaces, and FlowSync integration. It is a stable historical baseline rather than the current repository tip; the IDP branch descends from and extends it.

### Intelligent Document Processing

`platform/intelligent-document-processing` is an isolated document-intelligence platform track. The tag `v0.22-deterministic-purchase-order-demo` identifies the verified current milestone:

- authenticated and tenant-scoped;
- read-only UAT interface and API boundaries;
- deterministic purchase-order demonstration using synthetic data;
- structural ingestion/parsing and workflow/audit foundations;
- explicitly a technical preview, not a production document-processing service.

The current documented next milestone is **v0.22.1 Real Purchase-Order Accuracy Baseline**. No measured accuracy, universal layout support, production OCR/AI extraction, hosted customer upload workflow, persistent customer-document storage, completed human review, ERP posting, or active customer usage is established by repository evidence.

## Shared architecture

The tracks reuse Python data-processing, normalization, validation, logging, testing, and orchestration patterns. Later branches add workflow contracts and API/telemetry foundations. IDP additionally has isolated FastAPI, Supabase-auth, migration, and Vite/React boundaries.

Shared infrastructure does not erase product boundaries: competitor/product/price entities and workflows are not Document Intelligence document/tenant/workflow entities, and the original FlowSync dashboard is separate from the newer IDP UAT interface.

## Implemented capabilities

| Capability | Evidence state | Scope |
| --- | --- | --- |
| Generic ETL connectors, dataframe transforms, validation, CSV/SQLite loading, logging | Implemented | `main` |
| Competitor extraction, normalization, fuzzy matching, price history/change handling, alerts, reports/dashboard | Implemented but not fully verified | `feature/parser-v2` |
| Workflow contracts, DSL/definitions, DAG validation/construction, execution operations, telemetry and audit | Implemented | `workflow-runtime-stable` and descendants |
| Tenant-scoped authenticated read-only document API/UI | Implemented as UAT technical preview | `platform/intelligent-document-processing` |
| Deterministic synthetic purchase-order demonstration | Completed at v0.22 | `platform/intelligent-document-processing` |
| Real purchase-order accuracy baseline | Planned/current next milestone | v0.22.1 |
| Production readiness, measured extraction accuracy, customer deployments | Unsupported by repository evidence | None |

## Technology stack

- **Data and backend:** Python, pandas, NumPy (later branches), Requests, Beautiful Soup, lxml, SQLite, RapidFuzz, ReportLab, FastAPI, Uvicorn
- **Extraction/browser tooling:** Selenium and Playwright on later branches
- **Interfaces:** Streamlit; Vite, React, TypeScript, and React Router on the IDP frontend track
- **Identity/data platform:** Supabase authentication and tenant-membership foundations on the IDP branch
- **Testing:** pytest and Node's built-in test runner; branch-specific validation scripts
- **Deployment:** Vercel configuration for the IDP API and frontend technical previews

## Root project structure (`main`)

```text
project-root/
├── src/                    # Active ETL connectors, transforms, orchestration, state and loading
├── tests/                  # ETL extraction and orchestration tests
├── data/                   # Tracked placeholders for local data stages
├── output_data/            # Small retained example output
├── LEDGER/                 # Earlier duplicated ETL snapshot/reference
├── dashboard.py            # Streamlit ETL control surface
├── requirements.txt        # Main-branch Python dependencies
├── exchange_rates.csv      # Example transformation input
├── Banks.db                # Retained local-demo database
└── README.md               # Umbrella documentation
```

`code_file/`, `code_log/`, root log/output files, `src_backup/`, `src.zip`, and duplicated `LEDGER/` content are hygiene/technical-debt findings, not recommended source architecture. They remain untouched because their intended retention has not been established well enough for safe deletion.

## Branch-specific structure notes

- **Competitor Price Intelligence:** adds `workflows/`, `reports/`, price-history/output artifacts, dashboard/report generators, and broader tests. These paths are not present on `main`.
- **Workflow Runtime:** adds workflow runtime modules, API/telemetry foundations, workflow definitions, architecture documents, and expanded tests.
- **Intelligent Document Processing:** adds `api/`, `apps/flowsync-document-intelligence/`, `docs/`, `scripts/`, `supabase/`, `agents/`, `workspaces/`, `.github/`, `requirements-api.txt`, and `vercel.json`.

Inspect a branch without merging it:

```bash
git switch feature/parser-v2
git switch workflow-runtime-stable
git switch platform/intelligent-document-processing
```

Return to the default branch with `git switch main`.

## Setup

Use a separate environment for each branch because dependency manifests differ.

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the selected branch's Python dependencies:

```bash
python -m pip install -r requirements.txt
```

For the IDP Vercel API boundary, use `requirements-api.txt`. For the IDP frontend, use Node 22 and run `npm ci` inside `apps/flowsync-document-intelligence/`.

## Environment variables

`main` does not require committed credentials. The IDP branch provides `.env.example` placeholders including:

```dotenv
APP_ENV=uat
DOCUMENT_INTELLIGENCE_CORS_ALLOWED_ORIGINS=
SUPABASE_URL=
SUPABASE_PUBLISHABLE_KEY=
SUPABASE_JWKS_URL=
SUPABASE_JWT_ISSUER=
SUPABASE_JWT_AUDIENCE=authenticated
SUPABASE_SECRET_KEY=
SUPABASE_SERVICE_ROLE_KEY=
DATABASE_URL=
AUTH_MODE=
FLOWSYNC_TELEMETRY_ENABLED=false
```

Copy placeholders to a local `.env` or deployment secret manager and never commit real values. Browser code must not receive server-only keys.

## Run commands

On `main`:

```bash
python -m src.main
```

The root dashboard exists, but Streamlit is not declared in `main`'s `requirements.txt`; install it explicitly before running:

```bash
python -m pip install streamlit
streamlit run dashboard.py
```

On the IDP branch:

```bash
uvicorn api.index:app --reload
cd apps/flowsync-document-intelligence
npm ci
npm run dev
```

## Test and validation commands

On branches that declare pytest:

```bash
python -m pytest
```

IDP frontend validation:

```bash
cd apps/flowsync-document-intelligence
npm ci
npm run validate
npm run typecheck
npm test
npm run build
```

Tests that require browser binaries, network sources, Supabase, or deployment credentials may need additional local configuration. A missing credential should block that integration check, not be replaced with a committed value.

## Deployment and UAT links

These are technical previews, not production services:

- [Document Intelligence UAT frontend](https://flowsync-document-intelligence-uat.vercel.app)
- [Document Intelligence UAT API health](https://flowsync-document-intelligence-api.vercel.app/api/v1/health) — the bare deployment root currently returns 404; health and API documentation endpoints are reachable
- [Original FlowSync dashboard](https://flow-sync-beta.vercel.app/dashboard) — a separate Competitor Price Intelligence/workflow-monitoring interface; not the IDP UI

## Current limitations

- Branches contain separate product tracks and are substantially divergent from `main`.
- `main` still contains legacy bank-example naming, duplicated snapshots, generated logs/outputs, a local demo database, and backup archives.
- `main`'s dashboard dependency is not captured in its requirements file.
- Competitor matching and live-source reliability are not fully verified.
- Workflow Runtime is a retained baseline, not the latest platform branch.
- IDP v0.22 uses synthetic purchase-order data and deterministic behavior; no real-document accuracy baseline has been completed.
- Hosted previews depend on external Vercel/Supabase configuration not fully reproducible from repository files alone.

## Immediate next milestones

| Track | Evidence-based next milestone |
| --- | --- |
| ETL foundation | Consolidate duplicated/backup artifacts and align the dependency manifest with the runnable dashboard, after confirming which examples must remain |
| Competitor Price Intelligence | Correct and measure product-matching quality against controlled fixtures before broader live-source claims |
| Workflow Runtime | Clarify supported standalone runtime/version boundaries relative to the descendant IDP branch |
| Intelligent Document Processing | v0.22.1 Real Purchase-Order Accuracy Baseline using approved, safely handled real samples |

## Longer-term roadmap

- Separate deployable product tracks into clearer repositories or release boundaries if their independent histories continue.
- Add repeatable CI matrices for each supported branch and dependency set.
- Establish controlled evaluation datasets and publish methodology before reporting accuracy.
- Add OCR, mutation/upload, review, storage, and ERP boundaries only through explicit security and architecture milestones.
- Complete deployment ownership/runbooks before any production-readiness claim.

Roadmap items are planned directions, not implemented capabilities.

## Security and privacy boundaries

- Never commit `.env` files, tokens, private keys, service-role keys, customer documents, browser profiles, or deployment metadata.
- IDP v0.22 is authenticated, tenant-scoped, read-only, and synthetic-data-only.
- Supabase membership/permission checks and API-safe errors are part of the UAT boundary; they do not establish production certification.
- The repository contains no evidence authorizing storage or processing of private customer documents.
- Generated logs and outputs must be reviewed for sensitive content before sharing.

## Related repositories and interfaces

- **FlowSync:** separate Next.js dashboard repository for Competitor Price Intelligence and workflow monitoring; preview linked above.
- **ExploreAfrica:** separate travel administration repository with document-management foundations; it does not execute this repository's IDP pipeline.
- **Document Intelligence UAT:** frontend and API are implemented on the IDP branch of this repository and deployed as two separate Vercel projects.

## Contribution status

This is an owner-led portfolio/engineering repository with no documented open external contribution process. Before proposing changes, identify the target product track, branch from its authoritative branch, preserve product boundaries, and include tests plus evidence-based documentation.

## License and usage

No root license file is present. Source availability on GitHub does not grant reuse, modification, or redistribution rights. Treat the repository as all rights reserved unless the owner adds an explicit license.