# FlowSync Document Intelligence UI

This is the isolated FlowSync product UI for the Intelligent Document Processing Platform. It is separate from the internal Streamlit operator console, the legacy Competitor Price interface, and root `dashboard.py`.

The application consumes the versioned Document Intelligence API over HTTP. The API remains authoritative for identity, tenant scope, permissions, resource visibility, and errors. Frontend code must not import backend Python packages, repositories, runtime composition, Streamlit, or competitor-price modules.

## Current Phase

v0.17 Phase 1 establishes:

- the Vite, React, and TypeScript application boundary
- an enterprise app shell with sidebar and header
- route metadata and safe placeholder pages
- a GET-only API client and strict response-envelope parser
- fixed privacy-safe loading and error states
- theme foundations for later product views

Document data views are placeholders. Upload, correction, review decision, reprocess, workflow execution, and export actions are not implemented.

## Commands

Dependencies are intentionally not installed by repository automation.

```text
npm install
npm run typecheck
npm run build
npm run dev
```

`npm run lint` is a Phase 1 placeholder. A linter should be selected only with the approved FlowSync frontend toolchain.

## Configuration

The API base URL is read from `VITE_DOCUMENT_INTELLIGENCE_API_BASE_URL`. When omitted, the client uses `http://127.0.0.1:8001` for explicit local development. The application does not contact the API until a page invokes a query in a later phase.

Do not place credentials, tokens, tenant IDs, raw claims, storage paths, or backend configuration in Vite environment variables or browser-visible code.

