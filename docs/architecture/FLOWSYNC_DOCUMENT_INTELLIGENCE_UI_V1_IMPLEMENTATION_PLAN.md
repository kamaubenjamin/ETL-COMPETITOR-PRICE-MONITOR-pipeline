# FlowSync Document Intelligence UI v1 Implementation Plan

**Milestone:** v0.17
**Status:** Phases 1-3 implemented; Phase 4 not started

## 1. Milestone Overview

Implement a separate production-style, read-first FlowSync Document Intelligence application that consumes the versioned Document Intelligence API. The approved mockup guides information architecture and visual direction, but the milestone begins with product boundaries, host/toolchain confirmation, routing, API contracts, and safe states rather than pixel-perfect styling.

No phase may modify Streamlit, root `dashboard.py`, legacy `src/api/app.py`, competitor-price modules, backend repositories, or runtime composition. API additions and mutations require separate approval.

## 2. Global Requirements

- Confirm the actual FlowSync host repository/framework before creating UI source or dependencies.
- Keep Document Intelligence in an isolated app or feature package with no competitor-price domain imports.
- Consume only versioned Document Intelligence HTTP endpoints.
- Preserve API authority for identity, tenant scope, permissions, resource visibility, and errors.
- Keep all v0.17 actions read-only.
- Use typed API-local/view-model contracts and deterministic fixtures.
- Never expose raw documents, rows, corrections, claims, credentials, paths, stack traces, or backend internals.
- Support keyboard, screen-reader, and responsive behavior from the first shared components.
- Stop after each phase; never continue automatically.

## 3. Approved Source Layout

The approved application location is `apps/flowsync-document-intelligence/`. Phase 1 creates a standalone Vite, React, and TypeScript boundary with `app`, `api`, `pages`, `components`, `types`, `state`, and `styles` modules. It declares only frontend dependencies and imports no backend, Streamlit, or competitor-price source.

## 4. Phase 1: UI Boundary, App Shell, Routes, And API Client Contracts

**Completion:** Implemented. The isolated application has a responsive sidebar/header shell, all approved routes and static pages, safe status/loading/empty/error components, local TypeScript response models, branded endpoint builders, a GET-only client, strict standard-envelope validation, fixed privacy-safe errors, semantic theme foundations, README boundary guidance, and clear typecheck/build/lint scripts. No dependency install, lockfile, live API call, auth/session behavior, data view, mutation, backend change, Streamlit change, or competitor-price change was made.

### Scope

Confirm the FlowSync host/toolchain and establish the independent Document Intelligence application shell and GET-only API boundary.

### Expected Work

- Record the confirmed host, framework, package manager, test runner, and existing design-system primitives.
- Create the isolated application/feature package in the approved host.
- Add route constants/contracts for documents, document detail, validation, matching, review, workflows, audit, unauthorized, and unavailable pages.
- Add a clean enterprise shell with sidebar, top header, content region, error boundary, and responsive navigation skeleton.
- Define API envelope, pagination, filter, safe error, and request-state contracts.
- Implement a GET-only API client interface with explicit base URL and injected session adapter placeholder.
- Add deterministic fixtures; do not call a live API by default in component tests.
- Add an ADR addendum only if the confirmed host requires a materially different boundary.

### Tests

- Route uniqueness and deep-link parsing.
- Shell renders navigation and responsive states.
- API client accepts valid envelopes and rejects malformed envelopes.
- Only GET is exposed.
- Base URL/configuration is explicit and safe.
- Unauthorized, unavailable, and invalid-response mappings are fixed and privacy-safe.
- No backend, Streamlit, competitor-price, storage, or runtime imports.
- No token/credential persistence in feature code.

### Verification

Use the confirmed FlowSync host commands for type-check, unit tests, lint, and build. Also run repository boundary verification and `git diff --check` where this repository is modified.

### Stop Condition

Stop after shell, routes, contracts, and API client foundation. Do not build data pages or add backend contracts.

## 5. Phase 2: Document List And Detail Read-Only Views

**Completion:** Implemented. `/documents` now performs navigation-driven GET reads with API-compatible status/type filters, explicitly current-result search, safe status metrics, stable table columns, pagination totals, and fixed loading/empty/error states. `/documents/:documentId` composes existing detail, processing, validation, and matching GETs into safe metadata, summary cards, section tabs/placeholders, and processing history. Runtime payload projection rejects malformed records; state remains page-local and cancellation-safe; retry performs GET only; and API failures never activate fixtures. No protected preview, auth/session handling, upload, correction, decision, reprocess, workflow, export, backend, Streamlit, or competitor-price behavior was added. Dependency-free source validation passes; dependency-backed typecheck/build and browser visual verification remain pending.

### Scope

Implement the document dashboard, pagination/filters, and safe document detail views using existing GET endpoints.

### Expected Work

- Documents dashboard with status metrics, filter toolbar, stable table, pagination, and empty states.
- API-supported status and document-type filters.
- Current-page search only unless the API adds a separately approved search contract.
- Document detail metadata, processing status, and contextual navigation.
- Lifecycle/status display based only on returned state.
- Safe preview placeholder because no raw document preview contract exists.
- Loading, empty, unauthorized, forbidden, concealed-not-found, unavailable, and malformed-response states.

### Tests

- API data maps to stable view models without mutation.
- Filters and pagination serialize only allowlisted values.
- Status display handles every known and unknown value.
- Detail pages do not fetch raw storage paths/content.
- Error states preserve safe shell/navigation behavior.
- Responsive table/detail behavior and keyboard navigation.

### Verification

Run targeted API client, document feature, accessibility, responsive screenshot, type-check, lint, and build verification in the confirmed host.

### Stop Condition

Stop after read-only document list/detail. Do not add validation, matching, review, workflow, audit, upload, or action controls.

## 6. Phase 3: Validation, Matching, Review, Workflow, And Audit Views

**Status:** Implemented

### Scope

Implement all remaining read-only operational views supported by existing APIs.

### Expected Work

- Field/rule validation issue view with severity labels and safe messages.
- Matching candidate/confidence view without local match decisions.
- Review queue and review case detail with correction counts/history summaries and reprocess state.
- Disabled explanatory placeholders for extracted-vs-corrected values and future decisions where protected values/actions are unavailable.
- Workflow-run list and safe activity details.
- Lifecycle timeline only from explicitly correlatable API records.
- Audit list with event-type filters and allowlisted scalar metadata.

### Tests

- Stable projection and ordering for every view.
- No raw values, payloads, claims, paths, or arbitrary metadata render.
- No review, correction, workflow, or reprocess mutation calls exist.
- Confidence/severity/priority display includes accessible text, not color alone.
- Empty and partial-data states are deterministic.
- Existing API contract fixtures remain compatible.

### Verification

Run targeted feature/component tests, privacy scans, accessibility checks, type-check, lint, and build verification.

### Stop Condition

Stop after supported read-only views. Do not enable any action or request an API change automatically.

### Delivered

- Validation issue metrics/table and matching candidate/confidence views use bounded document API projections.
- Review queue/detail joins safe case, correction-summary, and dry-run reprocess-plan reads without protected values or commands.
- Workflow run summaries and audit events use deterministic tables/timelines; audit detail is restricted to an explicit scalar display allowlist.
- Shared confidence, severity, priority, read-only notice, and timeline components preserve accessible text labels.
- The dependency-free validator checks all Phase 3 pages/routes/functions, GET-only transport, mutation-surface absence, privacy strings, fixture fallback, and forbidden imports.
- `npm run validate` passes. Type-check, build, and browser screenshot verification were not run because dependencies are declared but not installed.

## 7. Phase 4: Auth/Tenant-Aware States And Error Hardening

### Scope

Integrate the approved FlowSync session boundary when available and harden all safe states without moving authorization into the UI.

### Expected Work

- Inject session credentials through one client adapter; feature modules never parse claims or store tokens.
- Display only approved user/workspace labels.
- Handle `401`, `403`, concealed `404`, invalid request, unavailable, timeout, safe `500`, and malformed envelope consistently.
- Preserve API request IDs as bounded support references where appropriate.
- Prove tenant query/filter controls cannot broaden scope.
- Add route guards only for user experience; every data request still relies on API authorization.
- Ensure no silent fallback to fixtures/local preview in integrated modes.

### Tests

- Identity/session adapter boundaries.
- Unauthorized/forbidden/not-found distinctions do not leak resource or tenant existence.
- Tenant identifiers/claims are absent from rendered output, URLs, logs, and storage.
- API unavailability cannot activate local data.
- Navigation visibility never substitutes for API authorization.
- Error boundaries do not reveal raw exceptions.

### Verification

Run auth-state, privacy, browser-storage, route, API compatibility, accessibility, type-check, lint, and build verification.

### Stop Condition

Stop after read-only auth/error hardening. Do not implement identity providers, login, tenant administration, or mutations unless separately approved.

## 8. Phase 5: Product Polish, Tests, And Integration Verification

### Scope

Bring the approved read-only product surface to demo/review quality and verify the complete client boundary.

### Expected Work

- Align information hierarchy with the approved mockup without requiring pixel parity.
- Finalize semantic tokens, density, table behavior, responsive navigation, loading skeletons, and empty/error states.
- Validate mobile, tablet, and desktop layouts.
- Complete keyboard/focus, screen-reader, contrast, and reduced-motion checks.
- Add API contract fixtures and an opt-in local API integration smoke path.
- Verify no competitor-price, Streamlit, backend, or runtime coupling.
- Document run/build/test instructions and known visual deviations.

### Tests

- Full UI unit/component/route suite.
- Accessibility and responsive browser matrix.
- API contract and GET-only integration smoke tests.
- Privacy and dependency boundary tests.
- Production build and bundle review using the existing host toolchain.
- No overlap, overflow, inaccessible labels, or hidden critical states at supported widths.

### Stop Condition

Stop after polish and verification. Do not add endpoints, protected previews, upload, review decisions, workflow execution, or export actions.

## 9. Phase 6: Release Closure And Handoff

### Expected Documentation

- v0.17 architecture summary
- future-agent handoff
- release notes
- final plan/ADR status
- roadmap, technical debt, and changelog updates

### Required Closure Evidence

- Confirmed source/host boundary.
- Route and API inventory.
- UI, accessibility, responsive, privacy, and boundary results.
- Explicit compatibility with existing API paths/envelopes.
- Known mockup deviations and deferred mutations.
- Owner-reviewed commit and tag recommendation.

### Stop Condition

Stop after release documentation and verification. Do not commit, push, or tag unless explicitly instructed.

## 10. API Compatibility Requirements

- Consume existing `/api/v1` GET routes without changing payload meanings.
- Validate the standard envelope and pagination metadata.
- Preserve request-ID behavior and safe API errors.
- Do not infer raw preview, correction values, lifecycle correlation, search, or action support where contracts do not exist.
- Any required additive endpoint is deferred to a separate API architecture/contract phase.

## 11. Boundary Requirements

- FlowSync imports no Python backend package or repository implementation.
- UI code imports no Streamlit module or provider.
- Document Intelligence feature code imports no competitor-price domain module.
- API client knows HTTP contracts only; pages do not construct runtime services.
- Permission and tenant decisions remain API-owned.
- Session/provider integration stays at the outer application boundary.

## 12. Visual And Component Requirements

- Follow the approved enterprise sidebar/header/dashboard direction.
- Use semantic tokens and existing design-system primitives where available.
- Keep status, confidence, severity, and priority understandable without color alone.
- Use stable table columns and responsive constraints.
- Provide explicit empty/loading/error cards and non-persistent placeholders.
- Treat final brand colors, typography, animation, and advanced polish as iterative work.

## 13. Risks And Mitigations

- **Unknown frontend host:** Phase 1 must confirm ownership/toolchain before files or dependencies are created.
- **Mockup overreach:** maintain a capability matrix linking each enabled surface to an existing API contract.
- **UI authorization drift:** API remains authoritative; route guards are convenience only.
- **Tenant leakage:** never accept tenant scope as a client-side security control or render raw tenant IDs.
- **Sensitive-value pressure:** use explicit unavailable placeholders until protected-value contracts exist.
- **Legacy coupling:** recursive import/dependency checks prevent competitor-price and Streamlit reuse.
- **Misleading search/counts:** label current-page projections and use server-supported filters only.
- **Production readiness confusion:** document that v0.16 production adapters and real identity remain unavailable.

## 14. Definition Of Done

- Independent FlowSync Document Intelligence app boundary is confirmed and implemented.
- App shell and proposed route set are stable.
- Existing API GET contracts drive all enabled views.
- Documents, validation, matching, review, workflow, and audit views are read-only and privacy-safe.
- Auth/tenant/error behavior preserves API authority.
- Approved mockup direction is represented without unsupported functionality.
- Accessibility, responsive, privacy, dependency, integration, and build verification pass.
- No Streamlit, competitor-price, backend repository, runtime, endpoint, migration, or mutation coupling is introduced.
- Summary, handoff, release notes, roadmap, debt, ADR, and changelog are complete.

## 15. Commit And Tag Strategy

Recommended owner-reviewed commits:

1. `feat: add FlowSync document intelligence app shell`
2. `feat: add read-only document views`
3. `feat: add document quality and review views`
4. `feat: harden FlowSync auth and error states`
5. `test: verify FlowSync document intelligence UI`
6. `docs: close v0.17 FlowSync document intelligence UI`

Recommended final tag after Phase 6 owner review:

`v0.17-flowsync-document-intelligence-ui`
