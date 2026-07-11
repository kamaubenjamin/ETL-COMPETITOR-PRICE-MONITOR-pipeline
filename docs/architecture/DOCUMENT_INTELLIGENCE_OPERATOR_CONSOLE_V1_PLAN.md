# Document Intelligence Operator Console v1 Plan

**Milestone:** v0.8
**Status:** Phases 1-2 implemented; live backend integration deferred

## Purpose

Provide document operators with one read-only workspace for inspecting document intake, processing, validation, matching, review, workflow, and audit activity. The console validates the information architecture for a future operational interface without coupling UI state to runtime ownership.

## Scope

v1 is a standalone Streamlit application at `src/ui/streamlit/document_intelligence_app.py`. It uses deterministic local fixtures through a provider/adapter boundary and includes sidebar filters, operational summary metrics, and nine task-oriented tabs.

The legacy competitor-price `dashboard.py` remains separate and unchanged.

## Information Architecture

- **Overview:** workload metrics, current document snapshot, and status distribution.
- **Inbox:** document identity, type, lifecycle status, confidence, and current stage.
- **Upload:** disabled placeholder; no file read, persistence, or backend call.
- **Processing:** active stage state and elapsed time.
- **Validation:** bounded issue severity, field, rule, and safe message.
- **Matching:** candidate identity, confidence, and match status.
- **Review Queue:** case reason, priority, lifecycle status, and assignment.
- **Workflow Runs:** workflow status, start time, and duration.
- **Audit Logs:** timestamp, event type, actor, and safe scalar metadata.

## Architecture Boundaries

- UI presents runtime-owned data and never owns business rules or lifecycle transitions.
- Review Runtime remains the source of truth for cases, corrections, decisions, and audit.
- Workflow Runtime remains the source of truth for execution.
- Display-only lifecycle strings are local to v1; no runtime internals are imported.
- No competitor-price, API, database, external service, OCR, or LLM imports are permitted.
- Mock records contain no real document payloads or sensitive values.

## Phase 2 Provider Architecture

- `data_providers.py` owns immutable module fixtures and returns defensive copies through `LocalOperatorConsoleProvider`.
- Provider methods expose documents, processing statuses, validation issues, matching results, review cases, workflow runs, audit events, and summary counts.
- `view_models.py` contains pure shaping functions that project provider records into stable JSON- and DataFrame-friendly display rows.
- `components.py` contains reusable metric, table, status-label, and section-header rendering helpers. Importing it does not render Streamlit elements.
- `document_intelligence_app.py` composes providers, view models, and components; it no longer owns fixture records.

Provider ordering is deterministic. Every call returns a fresh copy so table shaping or future display formatting cannot mutate fixture state.

## Interaction Model

Sidebar controls filter local tables by workspace, document type, workflow, runtime status, and review status. No action mutates data. Upload is visibly disabled to avoid implying persistence or backend capability.

## Future Integration

A later milestone may replace fixtures with a read-only application service or API contract. Integration must return bounded view models, authenticate operators, enforce authorization outside Streamlit, and submit all commands through runtime-owned services with idempotency and optimistic versions.

## Privacy And Security

- Never render raw full documents, complete source rows, correction payloads, credentials, or tokens in generic tables.
- Audit metadata must remain allowlisted, bounded, scalar, and safe for display.
- Do not expose corrected values without a future protected-value authorization boundary.
- Treat filenames and actor names as synthetic in v1 fixtures.

## Verification

```text
python -m py_compile src/ui/streamlit/document_intelligence_app.py
python -m py_compile src/ui/streamlit/data_providers.py
python -m py_compile src/ui/streamlit/view_models.py
python -m py_compile src/ui/streamlit/components.py
python -m pytest tests/ui/streamlit -q
python -m pytest tests/review_runtime -q
python scripts/verify_boundaries.py
git diff --check
git status --short --branch
```

## Definition Of Done

- The new app exists beside and independently from `dashboard.py`.
- All required filters, metrics, tabs, tables, lifecycle values, and mock datasets are represented.
- Display data is supplied through a defensive provider and pure view-model boundary.
- Provider determinism, filtering, copying, metric counts, and display shaping are covered by tests.
- Upload cannot persist or call a backend.
- Runtime boundaries remain compliant and Review Runtime regression tests pass.
- Release notes and repository trackers accurately describe the mock-data-only scope.

## Deferred Work

Backend adapters, API, persistence, authentication, authorization, mutation commands, protected-value viewing, production upload, OCR, LLM processing, notifications, accessibility testing, and deployment configuration are deferred.
