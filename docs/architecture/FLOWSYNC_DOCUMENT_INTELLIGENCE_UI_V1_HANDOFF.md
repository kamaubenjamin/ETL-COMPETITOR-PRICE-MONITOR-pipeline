# FlowSync Document Intelligence UI v1 Handoff

**Milestone:** v0.17
**State:** Implemented and verified; closed pending owner tag

## Current State

The repository contains an isolated, dependency-locked FlowSync Document Intelligence application at `apps/flowsync-document-intelligence/`. It provides responsive read-only views for documents, validation, matching, review, workflows, and audit data through the versioned Document Intelligence API. It starts safely without an API and displays bounded unavailable states rather than local fixtures.

The UI has no real identity/session integration and no mutation controls. Live data requires a separately running, correctly composed API.

## Important Files

- `apps/flowsync-document-intelligence/src/app/AppShell.tsx`: shell, navigation state, and keyboard behavior.
- `apps/flowsync-document-intelligence/src/app/routes.ts`: route catalog and matching.
- `apps/flowsync-document-intelligence/src/api/`: GET-only HTTP boundary, endpoint builders, envelope handling, and safe errors.
- `apps/flowsync-document-intelligence/src/pages/`: read-only product pages.
- `apps/flowsync-document-intelligence/src/components/`: reusable shell and display components.
- `apps/flowsync-document-intelligence/src/types/`: API-local and view-model types.
- `apps/flowsync-document-intelligence/src/styles/global.css`: semantic tokens and responsive presentation.
- `apps/flowsync-document-intelligence/scripts/validate-source.mjs`: dependency-free source/boundary/privacy validation.
- `docs/adr/ADR-022-flowsync-document-intelligence-ui-boundary.md`: governing frontend boundary.

## How To Run

From `apps/flowsync-document-intelligence/`:

```text
npm ci
npm run validate
npm run typecheck
npm run build
npm run dev
```

The development server binds to `http://127.0.0.1:4174`. Set `VITE_DOCUMENT_INTELLIGENCE_API_BASE_URL` only to the approved API origin; local development defaults to `http://127.0.0.1:8001`. Do not place credentials, tokens, tenant IDs, claims, or backend configuration in Vite variables.

Use `npm install` only when intentionally refreshing the dependency graph and review the resulting lockfile and audit output.

## Extension Rules

- Keep all backend access behind the versioned HTTP API.
- Add an endpoint to the allowlist before adding a consumer and keep existing envelope validation.
- Keep API payload projection separate from view-model shaping and presentation.
- Treat frontend route guards and hidden controls as usability only; the API must authorize every request.
- Preserve fixed safe error messages and concealed-resource behavior.
- Keep mutations absent until separately approved command contracts define authorization, idempotency, concurrency, audit, and error semantics.
- Add protected values or preview data only through explicit privacy-reviewed API contracts.
- Keep generated output and dependencies untracked.

## What Not To Change

- Do not import backend Python packages, repositories, Query Facade, Platform Runtime, or Document State.
- Do not import Streamlit or competitor-price code.
- Do not make tenant or permission decisions in the browser.
- Do not add fixture fallback for failed production reads.
- Do not expose tenant IDs, raw content, protected values, credentials, claims, backend paths, stack traces, raw exceptions, or unrestricted metadata.
- Do not modify root `dashboard.py` or legacy `src/api/app.py` as part of this product.

## UI And Backend Boundary

```text
FlowSync UI
  -> allowlisted GET-only HTTP client
  -> Document Intelligence API
  -> API authorization and runtime composition
  -> Query Facade / lifecycle / Document State
```

The API owns identity, tenant scope, permission enforcement, visibility, payloads, request IDs, and safe errors. The frontend owns presentation, navigation, local request state, and accessibility only.

## Known Risks And Deviations

- The UI is read-only and cannot complete operational mutations.
- Live authenticated API behavior has not been browser-verified.
- The API must run separately for live data.
- Final identity/session integration, production hosting, CSP, telemetry, and analytics are absent.
- Full screen-reader/contrast automation, tablet coverage, and E2E CI are deferred.
- Final brand theme and pixel-perfect polish remain future work.
- Nine optional API transport tests remain skipped; boundary verification reports two pre-existing U+FEFF warnings.

## Next Recommended Milestone

Plan v0.18 Export / Mutation API contracts before implementing ERP UI actions. Define command authorization, tenant enforcement, idempotency, optimistic concurrency, audit lineage, privacy-safe errors, and retry behavior first. ERP/export adapters and FlowSync controls should consume those approved contracts rather than writing runtime or repository state directly.

