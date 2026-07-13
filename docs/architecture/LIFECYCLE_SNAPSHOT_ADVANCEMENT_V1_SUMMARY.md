# Lifecycle Snapshot Advancement v1 Summary

**Milestone:** v0.14
**Status:** Implemented and verified; closed pending owner tag

## Milestone Purpose

v0.14 makes the mutable `DocumentRecord` projection reflect approved lifecycle progress while preserving append-only lifecycle events as the audit truth. It introduces one deterministic transition policy and one repository-neutral advancement service shared by ingestion, processing, review, and workflow writers.

The milestone does not activate concrete runtime producers, add public mutation endpoints, change API payloads, or modify Streamlit behavior.

## Delivered Capabilities

- `src/document_state/lifecycle/` package with dependency-light lifecycle contracts and policy.
- Immutable JSON-compatible transition, policy-decision, recovery-policy, and result contracts.
- Explicit transition catalog over the existing `DocumentStatus` vocabulary.
- Deterministic same-status no-op, invalid-transition rejection, terminal-state handling, and governed failed-state recovery.
- Repository-injected `LifecycleAdvancementService` using optimistic compare-and-swap updates.
- Status, current-stage, update-time, and version advancement without mutating lifecycle history.
- Optional lifecycle-service injection across all four Document State writer services.
- Audit-first append-then-advance behavior with bounded `projection_pending` outcomes.
- Idempotent replay that can repair a projection after a committed event and failed snapshot update.
- In-memory and SQLite backend equivalence, including SQLite reconstruction before readback.
- Read-after-advance verification through the Query Facade and existing API-provider shapes.
- Privacy, boundary, pagination, filter, and GET-only compatibility verification.

## Phase Summary

1. **Contracts and policy:** Added immutable lifecycle, recovery, decision, result, error, state, and transition-catalog contracts.
2. **Advancement service:** Added repository-neutral governed `DocumentRecord` projection updates with optimistic versions and safe result mapping.
3. **Writer integration:** Added optional service injection, policy prevalidation, idempotent event append, projection advancement, `projection_pending`, and replay repair.
4. **Read-after-advance verification:** Proved backend equivalence, SQLite reconstruction, Query Facade/API visibility, filters, pagination, privacy, replay, and GET-only compatibility.
5. **Release closure:** Re-ran focused and full verification and completed summary, handoff, release, roadmap, debt, plan, ADR, and changelog documentation.

## Current Architecture

```text
Writer services
  -> LifecycleAdvancementService
  -> DocumentRecord projection update
  -> Document State repositories
  -> DocumentStateQueryFacadeAdapter
  -> Workflow Query Facade
  -> Document Intelligence API
  -> Streamlit api_preview
```

Writers append lifecycle history before requesting projection advancement. Repository backends and the lifecycle service are supplied explicitly by composition; writers construct neither.

## Lifecycle Model

- Append-only lifecycle events remain the authoritative audit history.
- Mutable `DocumentRecord` is the current operational projection and can be rebuilt or repaired from approved events.
- Same-status replay is a no-op and does not increment the document version.
- `exported` is terminal.
- Recovery from `failed` requires an explicit `RecoveryPolicy` and an allowed target.
- `parsed` remains the structured-document equivalent.
- Reprocess planning alone does not advance document status.
- Review records remain independently governed after the document reaches `approved` or `exported`.
- Processing, review, and workflow records do not implicitly infer document transitions.

## Writer Behavior

- Writers may receive an optional injected `LifecycleAdvancementService`.
- Writers do not construct the service or select a repository backend.
- Without service injection, v0.13 append-only behavior remains unchanged.
- With injection, writers prevalidate policy, append the event idempotently, and then advance the projection.
- A projection version conflict after a committed event returns `projection_pending` where supported.
- Replaying the same event through a healthy service repairs the projection without duplicating history.

## Runtime Boundaries

- API and Streamlit remain read-only and do not import lifecycle services or Document State writers.
- Query Facade reads the advanced projection through `DocumentStateQueryFacadeAdapter`.
- Lifecycle policy and service do not import writers, API, UI, Query Facade, SQLite, composition, runtime implementations, storage, telemetry, or external services.
- Writers do not import API, Streamlit, Query Facade, persistence implementations, or concrete producer runtimes.
- Legacy `src/api/app.py`, root `dashboard.py`, and competitor-price modules remain untouched.

## API And UI Compatibility

- v0.9 endpoint paths and GET-only methods are unchanged.
- Payload meanings, response envelopes, pagination, request IDs, and security headers are unchanged.
- Existing status filters now reflect the advanced `DocumentRecord` projection.
- Streamlit `local_preview` and `api_preview` behavior is unchanged.
- No public mutation route or UI write action was added.

## Privacy And Safety

Lifecycle contracts, writer results, projection records, facade models, and API-provider results exclude raw documents, raw rows, raw correction values, artifact payloads, storage paths, credentials, stack traces, and raw exception messages. Metadata remains bounded and scalar-only where allowed.

## Verification Results

- Lifecycle suite: 63 passed.
- Writer suite: 80 passed.
- Document State suite: 318 passed.
- Document Intelligence API: 48 passed, 9 skipped.
- Workflow Query Facade, Streamlit, and Review Runtime: 266 passed.
- Full regression: 1,309 passed, 9 skipped, 711 warnings.
- Runtime boundary verification: compliant, with two pre-existing U+FEFF scan warnings.
- Lifecycle and all four writer service modules compile successfully.
- Four known legacy files generated by the full suite were restored.
- `git diff --check`: passed.

## Backward Compatibility

The milestone is additive. Existing repository interfaces, document status values, writer commands, Query Facade read models, API paths and payload meanings, Streamlit modes, and append-only writer construction remain compatible. Advancement occurs only when the service is explicitly injected.

## Deferred Work

- Runtime producer adapters and production composition activation.
- Repository-backed verification of recovery policies against reprocess plans.
- Cross-record units of work, transactional outbox, and background reconciliation.
- Bulk historical projection rebuild and backfill tooling.
- Public mutation endpoints and upload UI/API.
- Authentication, authorization, and tenant isolation.
- PostgreSQL/Supabase production repositories.
- Encrypted raw blob storage and retention controls.
- FlowSync Document Intelligence.
- OCR, LLM processing, and external services.
