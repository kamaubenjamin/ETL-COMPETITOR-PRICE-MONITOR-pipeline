# FlowSync Document Intelligence UI v1 Summary

**Milestone:** v0.17
**Status:** Implemented and verified; closed pending owner tag

## Milestone Purpose

v0.17 establishes a separate production-style Document Intelligence frontend without coupling product presentation to backend Python packages, Streamlit, or the legacy Competitor Price product. The delivered application is deliberately read-only and consumes the versioned Document Intelligence API as its authoritative source for data, identity, tenant scope, permissions, visibility, and errors.

## Delivered Capabilities

- Isolated Vite, React, and TypeScript application at `apps/flowsync-document-intelligence/`.
- Responsive application shell with sidebar, header, stable navigation, mobile menu semantics, and skip-to-content support.
- Explicit route/page contracts for documents, quality views, review, workflows, audit, runtime preview, unauthorized, and unavailable states.
- GET-only API client with allowlisted endpoints, bounded filters, strict standard-envelope validation, safe request IDs, and fixed non-reflective errors.
- Read-only document list and detail views with current-result filtering, status summaries, processing history, and safe metadata projections.
- Read-only validation, matching, review queue/detail, workflow-run, and allowlisted audit views.
- API-authoritative unauthorized, forbidden, concealed-not-found, unavailable, and malformed-response handling.
- Semantic status, severity, priority, confidence, loading, empty, and error presentation.
- Lockfile-controlled dependency graph, advisory-free Vite toolchain, strict TypeScript verification, production build, and generated-output guards.
- Desktop and mobile rendered smoke verification with deep-link, no-API startup, keyboard, and responsive checks.

## Phase Summary

1. **Boundary and shell:** Created the isolated app, route catalog, responsive shell, safe components, local HTTP contracts, and GET-only client.
2. **Document views:** Added API-backed document list/detail, processing, validation, and matching summaries with no fixture fallback.
3. **Operational views:** Added validation, matching, review, workflow, and audit pages with bounded privacy-safe projections.
4. **Access and availability:** Normalized safe request states and retained API authority for permissions, tenant scope, and resource visibility.
5. **Verification and polish:** Installed and locked dependencies, removed known advisories, passed validation/typecheck/build, and verified desktop/mobile rendering and keyboard basics.
6. **Release closure:** Completed the architecture summary, future-agent handoff, release notes, and milestone status records.

## UI Architecture

```text
FlowSync Document Intelligence UI
  -> GET-only API client
  -> Document Intelligence API
  -> Platform Runtime
  -> Document State / Lifecycle / Query Facade
```

The frontend imports no backend Python package. It does not import Streamlit or competitor-price modules, select runtime dependencies, enforce permissions, or filter tenant data as a security control. The API remains authoritative.

## Route Coverage

- `/documents`
- `/documents/:documentId`
- `/documents/:documentId/validation`
- `/documents/:documentId/matching`
- `/review`
- `/review/:reviewCaseId`
- `/workflows`
- `/audit`
- `/settings/runtime-preview`
- `/unauthorized`
- `/unavailable`

## Read-Only Safety Model

The client issues GET requests only. It has no fixture fallback and makes no module-import or startup request. It provides no upload, correction submission, review decision, reprocess, workflow-run, export, or other mutation action. The UI never treats navigation visibility as authorization.

## Privacy Rules

Rendered content, errors, logs, URLs, and browser-visible configuration exclude tenant IDs, raw documents, raw rows, protected correction values, artifact payloads, credentials, tokens, raw claims, backend paths, stack traces, raw exception messages, and unrestricted audit metadata.

## Verification Results

- `npm run validate`: passed for 52 frontend source files.
- `npm run typecheck`: passed.
- `npm run build`: passed with Vite 8.1.4.
- `npm audit --audit-level=moderate`: zero known vulnerabilities.
- Document Intelligence API tests: 80 passed, 9 skipped.
- Platform Runtime tests: 84 passed.
- Security tests: 60 passed.
- Runtime boundary verification: compliant, with two pre-existing U+FEFF scan warnings.
- `git diff --check`: passed.

Visual verification covered desktop `1440x1000`, mobile `390x844`, all primary deep links, safe no-API/unavailable states, the display-only runtime preview, fixed unauthorized/unavailable pages, mobile-menu Escape behavior, and skip-to-content focus.

## Compatibility Notes

- No backend endpoint, method, payload meaning, envelope, authorization behavior, migration, or runtime composition changed.
- Streamlit remains the separate internal operator console.
- Root `dashboard.py`, legacy `src/api/app.py`, and Competitor Price modules remain untouched.
- The API must run separately for live data; unavailable transport fails safely without fixture substitution.

## Deferred Work

- Live authenticated API integration verification and a real session/login/identity-provider adapter.
- Versioned upload, correction, review-decision, reprocess, workflow-run, export, and other mutation contracts and UI.
- Protected document preview and protected correction-value access.
- Richer design-system theming and final pixel-level brand polish.
- Full screen-reader/contrast audit, broader viewport coverage, and E2E browser automation in CI.
- FlowSync deployment/hosting, CSP, telemetry, analytics, and operational ownership.
- ERP/export UI integration and its required authorization, idempotency, audit, and error contracts.

