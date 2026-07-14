# FlowSync Document Intelligence UI

This is the isolated FlowSync product UI for the Intelligent Document Processing Platform. It is separate from the internal Streamlit operator console, the legacy Competitor Price interface, and root `dashboard.py`.

The application consumes the versioned Document Intelligence API over HTTP. The API remains authoritative for identity, tenant scope, permissions, resource visibility, and errors. Frontend code must not import backend Python packages, repositories, runtime composition, Streamlit, or competitor-price modules.

## Milestone State

v0.17 is implemented, verified, and tagged. v0.18 and v0.19 are implemented, verified, and closed pending their owner tags. v0.18 adds the read-only export-readiness/history placeholder and disabled export action. v0.19 adds the guarded upload metadata preview and read-only processing timeline. The UI foundation establishes:

- the Vite, React, and TypeScript application boundary
- an enterprise app shell with sidebar and header
- route metadata and safe placeholder pages
- a GET-only read client, one guarded JSON metadata-preview POST, and strict response-envelope parsers
- fixed privacy-safe loading and error states
- theme foundations for later product views
- a real read-only document dashboard backed by `GET /api/v1/documents`
- safe status/type request filters and current-result search
- a read-only document detail view backed by document, processing, validation, and matching GET endpoints
- runtime payload validation, stable view-model shaping, and a dependency-free source validator
- read-only validation, matching, review, workflow, and audit views
- normalized API-authoritative access, unavailable, concealed-resource, and malformed-response states
- dependency-locked Vite/React/TypeScript builds with zero known npm advisories
- desktop/mobile rendered smoke verification and keyboard-accessible shell navigation

Raw preview, file transfer/staging, correction, review decision, reprocess, workflow execution, and enabled export actions are not implemented. v0.18 Phase 5 adds a read-only document export-readiness panel and safe GET-only attempt-history projection. v0.19 Phase 5 adds `/uploads`, an explicit JSON metadata validation preview, browser-local file metadata inspection, recent upload reads, supplied-event processing timelines, manual refresh, and document processing-status projection. The preview treats staging-disabled as the expected governed state and never transmits document content. Export remains disabled, mutation activation is deferred, and no ERP adapter is connected.

## Commands

Install the lockfile-defined dependency graph before running the app:

```text
npm ci
npm run validate
npm run typecheck
npm run build
npm run dev
```

Use `npm install` only when intentionally refreshing dependencies; review `package-lock.json` and run `npm audit --audit-level=moderate` afterward.

`npm run validate` performs dependency-free source checks for routes, scripts, GET-only reads, the single guarded metadata-preview POST, absence of file-content transmission APIs, generated-directory tracking, boundaries, and privacy. The development server binds to `http://127.0.0.1:4174`. `npm run lint` remains a placeholder until frontend lint tooling is approved.

## Configuration

The API base URL is read from `VITE_DOCUMENT_INTELLIGENCE_API_BASE_URL`. When omitted, the client uses `http://127.0.0.1:8001` for explicit local development. The application starts without a live API and displays fixed safe unavailable states when reads cannot complete.

Do not place credentials, tokens, tenant IDs, raw claims, storage paths, or backend configuration in Vite environment variables or browser-visible code.
