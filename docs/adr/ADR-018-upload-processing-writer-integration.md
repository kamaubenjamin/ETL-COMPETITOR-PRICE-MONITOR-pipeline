# ADR-018: Upload-to-Processing Writer Integration v1

## Status

Accepted. Phases 1-4 are implemented and verified; release closure remains pending. Runtime producer adapters remain deferred from the current internal writer foundation.

## Context

v0.11 defined persistence-neutral Document State records and repository ports. v0.12 added durable SQLite repositories, shared conformance, and explicit in-memory/SQLite composition. The approved read path can project repository state through Workflow Query Facade and the Document Intelligence API, but actual upload, ingestion, workflow, validation, matching, and review outcomes do not populate Document State.

The integration must preserve runtime ownership, privacy, deterministic retries, repository semantics, and API/UI read-only behavior. Existing runtime result objects can contain raw document content, paths, rows, entity data, artifacts, correction values, or exception text and therefore cannot be persisted wholesale.

## Decision

Add internal writer contracts and services under:

```text
src/document_state/writers/
```

Document State writers own normalized commands, record construction, privacy projection, deterministic IDs, idempotency keys, version rules, write ordering, and safe operation results. They depend only on public/package-local Document State contracts and injected repository ports.

Runtime-specific adapters remain on the producer side:

```text
Document Engine public results -> Document Engine adapter -> writer commands
Workflow public results        -> Workflow adapter        -> writer commands
Review public results          -> Review adapter          -> writer commands
```

The adapters may inspect approved public result fields but must not pass complete serialized results or raw artifacts to writers.

## Package Decision

`src/document_state/writers/` is selected because persistence mapping and consistency invariants belong to Document State. `src/workflow_runtime/writers/document_state/` is rejected because Workflow Runtime does not own ingestion or review outcomes. `src/ingestion_runtime/document_state_writers/` is rejected because no standalone ingestion runtime exists and the scope spans multiple producers.

This decision does not make Document State depend on runtime implementations. Producer-specific imports remain outside the writer package.

## Command Decision

Writer commands are immutable, JSON-compatible, bounded, and backend-neutral. They contain only stable identities, statuses, timestamps, counts, safe codes/messages, and opaque references required to construct existing Document State records.

Commands must reject raw document content, rows, source payloads, correction values, matching entity/master payloads, artifact payloads, stack traces, credentials, storage paths, OCR output, and arbitrary metadata.

Stable IDs and source event identities are supplied or deterministically derived by producer adapters. Writer services do not generate random identities during retry.

## Idempotency Decision

- Append-only writes use domain-separated deterministic idempotency keys and existing repository content-hash conflict behavior.
- Identical retries return existing records; key or stable-ID reuse with different canonical content conflicts.
- Initial mutable creates use read-compare-create. If a create race conflicts, the service re-reads and accepts only an identical safe record.
- Unknown conflicts are never treated as successful retries.
- Operation IDs and timestamps remain stable across retries.

## Version Decision

Document, processing, review, and workflow snapshots use explicit caller-visible `expected_version`. Updates must construct version `expected_version + 1` and use existing compare-and-swap repository methods. Stale versions fail safely; writers do not use last-write-wins or hidden automatic version retries.

Lifecycle, validation, matching, correction, reprocess, and audit records remain append-only.

## Transaction And Failure Decision

One repository operation remains one transaction. v0.13 does not add a cross-record unit of work.

Writer services prevalidate complete command batches, write in a deterministic checkpoint order, and return bounded committed-operation details. If a later operation fails, earlier operations remain and an identical retry resumes through existing create comparison and append idempotency. Writers do not delete history or claim distributed exactly-once delivery.

Success audit events are appended only after their corresponding state operation succeeds. Failure recording uses fixed safe codes and is best effort if the state source itself is unavailable.

## Artifact Reference Decision

Only opaque bounded `artifact_ref_id`, `artifact_kind`, and source-stage references may cross the writer boundary. They may be persisted only in explicit fields or narrowly allowlisted scalar metadata after privacy review.

Document State does not own artifact storage, retrieval, authorization, retention, or deletion. Raw encrypted blob storage remains a separate future boundary.

## Composition Decision

An application composition root selects `in_memory` or `sqlite` through existing `DocumentStateComposition`, then explicitly injects repository ports into writer services. Writers and producer adapters do not inspect environment variables, construct repositories, import engine modules, or fall back between backends.

No API, Streamlit, or Workflow Query Facade module receives a writer port in v0.13. Public mutation endpoints remain deferred.

## Read-After-Write Decision

The verified path will be:

```text
Upload / processing producer
  -> producer adapter
  -> Document State writer
  -> Document State repositories
  -> DocumentStateQueryFacadeAdapter
  -> Workflow Query Facade
  -> Document Intelligence API
  -> Streamlit api_preview
```

Existing API paths, GET-only methods, successful payload meanings, envelopes, pagination, request IDs, security headers, and Streamlit modes must remain unchanged.

## Consequences

### Positive

- Real local/dev runtime outcomes can populate the established operational state boundary.
- Retry, version, privacy, and mapping behavior become explicit and testable.
- Both active repository backends share one writer contract.
- API/UI remain isolated from repositories and mutation logic.
- Future PostgreSQL can reuse writer and conformance behavior.

### Negative

- Producer adapters are required for several runtimes.
- Multi-record state transitions can be partially committed and require deterministic replay.
- Create idempotency requires a narrow read dependency in addition to write ports.
- Lifecycle stage/status mapping requires governance as runtimes evolve.
- Synchronous writer calls do not provide an outbox or distributed delivery guarantee.

## Deferred Decisions

- Cross-record unit-of-work and transactional outbox.
- PostgreSQL/Supabase implementation and production composition activation.
- Public mutation APIs and Streamlit actions.
- Upload transport, raw encrypted blob storage, and malware/content scanning.
- Authentication, authorization, tenant isolation, rate limiting, CORS/gateway/TLS.
- Production telemetry, backup/recovery, retention/archive/legal hold.
- FlowSync Document Intelligence, OCR, LLM processing, and external services.

## Compatibility

ADR-018 is additive to ADR-016 and ADR-017. It preserves Document State records/repository ports unless a separately reviewed additive artifact-reference metadata allowlist is required. It preserves v0.10 Query Facade contracts, v0.9 API contracts, Streamlit behavior, legacy API/dashboard, and competitor-price separation.
