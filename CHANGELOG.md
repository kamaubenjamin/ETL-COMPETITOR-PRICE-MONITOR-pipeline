.\venv\Scripts\Activate.ps1# Changelog

## Unreleased

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
