.\venv\Scripts\Activate.ps1# Changelog

## Unreleased

- Added v0.12 Durable Document State Phase 2 with file-backed standard-library SQLite repositories for all ten Document State record families, explicit relational schema columns, transactional checksum-verified migrations, deterministic filter/order/pagination behavior, optimistic compare-and-swap updates, append idempotency, canonical privacy-safe metadata JSON, and close/reopen durability while preserving API/UI boundaries.

- Added v0.12 Durable Document State Phase 1 with explicit in-memory/SQLite/deferred-PostgreSQL configuration, privacy-safe persistence errors, deterministic metadata for eleven planned tables, immutable migration and applied-ledger contracts, and sequence/engine/checksum validation; SQL, database connections, repositories, API/UI integration, and file/network behavior remain deferred.

- Closed and tagged v0.11 Persistent Document State with ten immutable privacy-safe record families, bounded repository contracts, deterministic lock-protected in-memory repositories, optimistic versions, append idempotency, a read-only Workflow Query Facade adapter, recursive boundary/privacy verification, full regression verification, and release handoff documentation.

- Closed and tagged v0.10 Workflow Query Facade with frozen privacy-safe read models, bounded pagination, structural read ports, a deterministic immutable in-memory facade, a preferred API-side facade adapter, recursive import/privacy verification, bounded facade-error mapping, full regression verification, and release handoff documentation while preserving v0.9 routes, envelopes, payload meanings, filters, pagination, security headers, request IDs, and GET-only behavior.

- Closed and tagged v0.9 Document Intelligence API Foundation with a separate read-only FastAPI app, deterministic preview endpoints, strict envelopes and pagination, optional GET-only Streamlit adapter, bounded request IDs, safe global errors, conservative security headers, disabled-by-default CORS, boundary compliance, full regression verification, and release handoff documentation.

- Closed and tagged v0.8 Document Intelligence Operator Console Streamlit v1 with deterministic local document, validation, matching, workflow, and audit fixtures; defensive provider/view-model layers; reusable display components; a read-only Review Runtime preview; grouped operational navigation; status/priority labels; filtered empty states; run-mode safety messaging; a non-persistent upload placeholder; full regression verification; and release handoff documentation.

- Closed and tagged v0.7 Review / Correction Runtime with immutable contracts, an explicit lifecycle state machine, deterministic in-memory case services, field-level controlled corrections, five reviewer decisions, append-only audit lineage, and declarative dry-run reprocess planning.

- Closed and tagged v0.6 Extraction & Transformation Capability Hardening with versioned deterministic plans, real `TransformStage` execution, field/regex mapping, data validation, stable sorting, grouped/dataset aggregation, privacy-safe metadata, legacy compatibility, and end-to-end workflow verification.

- Added Workflow Runtime Locking v1 (v0.5) — database-backed row-level locking with execution leases, file-based fallback, idempotency key deduplication, and comprehensive test suite (158/158 locking tests passing).
- Added Entity Runtime Concurrency Hardening (v0.5) — versioned entity persistence, optimistic and pessimistic locking, execution leasing, idempotency protection, graceful degradation, and verification coverage.
- Added CI Contract Validation v1 with a lightweight GitHub Actions workflow for contract tests and standalone registry validation.
- Closed Contract Registry v1 with JSON Schema Draft 07 schemas, examples, local validation tooling, closure documentation, roadmap updates, and release notes.
- Added FlowSync Supabase telemetry integration with reusable contracts, retry-aware REST client, and `.env`-driven credentials.
- Added structured pipeline, ingestion, and alert telemetry services for `pipeline_runs`, `ingestion_logs`, and `operational_alerts`.
- Instrumented the classic ETL orchestrator, multi-source pipeline, and workflow runner without making telemetry a hard runtime dependency.
- Added extension points and comments for future Kafka publishing, Airflow orchestration, async workers, and distributed ingestion.
- Added telemetry tests and `.env.example` for production configuration.
- Added API-first FlowSync control-plane boundary with typed contracts, async-safe workflow execution service, run status tracking, source health, connector test, source sync, alerts, telemetry run, and latest report endpoints.
- Added optional FastAPI/uvicorn API deployment dependencies.
- Added standardized connector architecture under `src/connectors`, canonical product records, structured execution logging, reusable transformation pipeline, standardized execution statuses, safer workflow metadata, retry/timeout status handling, overlap prevention, and normalized API payloads.
- Added `SmartPlaywrightConnector`, ecommerce/supermarket DOM heuristics, detergent workflow examples for Naivas and Quickmart, product identity normalization, comparison utilities, and smart extraction documentation.
