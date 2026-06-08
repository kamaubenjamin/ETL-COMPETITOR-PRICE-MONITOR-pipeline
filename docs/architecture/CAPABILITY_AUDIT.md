# Repository Capability Audit

**Date:** 2026-06-05  
**Scope:** Entire ETL Competitor Price Monitor pipeline  
**Format:** For each capability — Exists (Yes/No/Partial), Location, Key Files, Maturity, Gaps, Recommended Improvements

---

## 1. Workflow Engine

| Dimension | Assessment |
|---|---|
| **Exists** | **Yes** |
| **Location** | `src/workflow_runtime/` |
| **Key Files** | `dsl/workflow_parser.py`, `dsl/workflow_validator.py`, `dag/builder.py`, `runtime/workflow_runner.py`, `operations/*.py` (9 stage types), `contracts/workflow_definition.py`, `contracts/execution_context.py`, `contracts/workflow_result.py`, `workspace/workspace_registry.py`, `locking/*.py` (3 lock providers, idempotency, execution guard) |
| **Maturity** | **Mature** |
| **Gaps** | 1. DAG is linear (no parallel or conditional branches). 2. No per-stage timeout configuration. 3. No lifecycle hooks (pre/post/on_error) on `BaseStage`. 4. No cancellation/pause/resume mechanism. 5. No retry logic with backoff per stage (only workflow-level retry in `WorkflowExecutionService`). 6. Stages pass `DataFrame` via in-memory `context.data` — no streaming for large datasets. |
| **Recommended Improvements** | 1. Add parallel/conditional branch support to `DAGBuilder`. 2. Add stage-level timeout config. 3. Add `pre_execute`/`post_execute`/`on_error` hooks to `BaseStage`. 4. Implement cancellation token propagation. 5. Add per-stage retry with exponential backoff. 6. Consider chunked/streamed DataFrame passing for large workloads. |

---

## 2. Rule Engine

| Dimension | Assessment |
|---|---|
| **Exists** | **Partial** |
| **Location** | `src/transforms/pipeline.py`, `src/workflow_runtime/operations/filter_stage.py`, `src/transform/engine.py` |
| **Key Files** | `transforms/pipeline.py` (rename rules, null handling, filters, type coercion, deduplication, normalization), `transform/engine.py` (transformation rule pipeline), `workflow_runtime/operations/filter_stage.py`, `workflow_runtime/operations/transform_stage.py` |
| **Maturity** | **Early** |
| **Gaps** | 1. Rules are Python dicts/code, not a DSL with serializable format. 2. No rule chaining/sequencing language. 3. No rule priority or conflict resolution. 4. No conditional rule execution (IF-THEN-ELSE). 5. No rule versioning or audit trail. 6. Rules are not loadable from external configuration; hardcoded in Python modules. |
| **Recommended Improvements** | 1. Design and implement a declarative rule DSL (e.g., JSON-based rule definitions with conditions and actions). 2. Add rule chaining with priority ordering. 3. Add condition evaluation (IF field > value THEN action). 4. Add rule audit logging. 5. Support external rule loading from JSON/YAML files. |

---

## 3. Transformation Engine

| Dimension | Assessment |
|---|---|
| **Exists** | **Yes** |
| **Location** | `src/transform/`, `src/transforms/`, `src/workflow_runtime/operations/transform_stage.py` |
| **Key Files** | `transform/transformer.py`, `transform/engine.py`, `transform/intelligence_engine.py`, `transform/product_normalizer.py`, `transform/product_parser.py`, `transform/comparison_engine.py`, `transform/cleaners.py`, `transform/analyzers.py`, `transforms/pipeline.py`, `transforms/product_identity.py`, `transforms/comparison.py` |
| **Maturity** | **Maturing** |
| **Gaps** | 1. No streaming/chunked transformation — operates on entire DataFrames in memory. 2. No execution plan caching or re-use. 3. `intelligence_engine.py` overlaps significantly with `product_normalizer.py` (duplicate model/size regex patterns). 4. No transformation metrics (rows transformed, error count, duration per rule). 5. No dry-run or preview mode for transformations. |
| **Recommended Improvements** | 1. Add streaming transformation stage for large datasets. 2. Deduplicate between `intelligence_engine.py` and `product_normalizer.py`. 3. Add per-transformation metrics collection. 4. Add dry-run/preview mode. 5. Add transformation result diffing (before/after comparison). |

---

## 4. Regex Mapping

| Dimension | Assessment |
|---|---|
| **Exists** | **Partial** |
| **Location** | `src/transform/product_parser.py`, `src/transform/product_normalizer.py`, `src/transform/intelligence_engine.py`, `src/transforms/product_identity.py` |
| **Key Files** | `product_parser.py` (price/currency regex), `product_normalizer.py` (model/size/specs regex), `intelligence_engine.py` (model/size/specs regex), `product_identity.py` (unit regex) |
| **Maturity** | **Low** |
| **Gaps** | 1. No centralized regex mapping registry — patterns are hardcoded inline across 4+ files. 2. Duplicate patterns exist (`product_normalizer.py` and `intelligence_engine.py` both define identical model regexes). 3. No configurable/loadable regex from external configuration. 4. No regex testing utilities or validation framework. 5. No support for user-defined or source-specific regex overrides. 6. No named capture group standardization. |
| **Recommended Improvements** | 1. Create a centralized regex mapping registry (`src/transform/regex_registry.py`) with loadable config. 2. Deduplicate patterns between `product_normalizer.py` and `intelligence_engine.py`. 3. Support external regex configuration via JSON/YAML. 4. Add regex validation tests. 5. Add source-specific regex overrides by source type. 6. Standardize named capture groups across all patterns. |

---

## 5. Field Mapping

| Dimension | Assessment |
|---|---|
| **Exists** | **Partial** |
| **Location** | `src/transforms/pipeline.py`, `src/workflow_runtime/operations/transform_stage.py` |
| **Key Files** | `transforms/pipeline.py` (rename rules, column mapping), `workflow_runtime/operations/transform_stage.py` (field-level transformations via rules) |
| **Maturity** | **Early** |
| **Gaps** | 1. Mapping is Python code, not declarative (no JSON/YAML field mapping definitions). 2. No visual mapping interface. 3. No type coercion mapping (string→float, etc.) except basic handling in `transforms/pipeline.py`. 4. No field-level transformation functions. 5. No source→target field mapping with configurable transformations. |
| **Recommended Improvements** | 1. Create a declarative field mapping DSL (source_field → transform_function → target_field). 2. Add type coercion mapping declarations. 3. Add support for field concatenation/splitting in mapping. 4. Add default value and null handling in field mapping. 5. Support nested field mapping (JSON flatten/unflatten). |

---

## 6. Validation

| Dimension | Assessment |
|---|---|
| **Exists** | **Partial** |
| **Location** | `src/entity_runtime/validation/validator.py`, `src/document_engine/validation/`, `src/workflow_runtime/dsl/workflow_validator.py`, `src/transform/cleaners.py` |
| **Key Files** | `entity_runtime/validation/validator.py`, `document_engine/validation/structural_validator.py`, `document_engine/validation/quality_scorer.py`, `document_engine/validation/validation_orchestrator.py`, `workflow_runtime/dsl/workflow_validator.py`, `transform/cleaners.py` |
| **Maturity** | **Early** |
| **Gaps** | 1. No production-grade data validation framework (no schema validation, no constraint validation, no row-level validation rules). 2. `entity_runtime/validation/validator.py` is a shell/stub. 3. `document_engine` validators are document-structural only (not data validation). 4. No user-configurable validation rules. 5. No validation error aggregation or reporting. 6. No data quality scoring (document engine has quality scorer but data-level doesn't). |
| **Recommended Improvements** | 1. Build a data validation framework with schema comparison, constraint validation, and row-level rule engine. 2. Add configurable validation rules (e.g., min/max, not null, unique, regex pattern). 3. Add validation error aggregation with severity levels. 4. Add validation report generation. 5. Add data quality scoring for extracted/transformed data. |

---

## 7. Filtering

| Dimension | Assessment |
|---|---|
| **Exists** | **Yes** |
| **Location** | `src/workflow_runtime/operations/filter_stage.py` |
| **Key Files** | `workflow_runtime/operations/filter_stage.py`, `transform/cleaners.py` (basic row filtering), `transforms/pipeline.py` (filter rules) |
| **Maturity** | **Early** |
| **Gaps** | 1. Filter expressions are limited (column + operator + value). 2. No compound filter logic (AND/OR/NOT combinators). 3. No filter chaining. 4. No regex or pattern-based filters. 5. No null/invalid value filtering. 6. `filter_stage.py` appears to be a basic implementation with limited operator support. |
| **Recommended Improvements** | 1. Extend filter operations to support compound conditions (AND/OR/NOT). 2. Add pattern/regex filter support. 3. Add null value filter. 4. Add filter chaining with pipeline. 5. Add filter evaluation metrics (rows in/out). |

---

## 8. Sorting

| Dimension | Assessment |
|---|---|
| **Exists** | **No** |
| **Location** | N/A |
| **Key Files** | None |
| **Maturity** | **Not implemented** |
| **Gaps** | 1. No sorting stage in the workflow runtime. 2. No sorted output capability for export/reports. 3. Sorting relies on ad-hoc DataFrame sort calls in Python code, not a reusable capability. 4. No sort configuration in workflow definitions (WF JSON). |
| **Recommended Improvements** | 1. Add a `SortStage` to `workflow_runtime/operations/` with configurable sort columns and direction. 2. Support multi-column sort. 3. Add sort configuration to workflow definition schema. |

---

## 9. Aggregation

| Dimension | Assessment |
|---|---|
| **Exists** | **No** |
| **Location** | N/A |
| **Key Files** | None |
| **Maturity** | **Not implemented** |
| **Gaps** | 1. No aggregation stage in the workflow runtime. 2. No GROUP BY / SUM / AVG / COUNT / MIN / MAX capability. 3. No pivot/cross-tab support. 4. No time-series aggregation (hourly/daily/weekly rollups). 5. Relies on ad-hoc Pandas groupby() in Python code. |
| **Recommended Improvements** | 1. Add an `AggregationStage` to `workflow_runtime/operations/` supporting group-by, sum, avg, count, min, max. 2. Add time-series aggregation. 3. Add pivot/cross-tab support. 4. Add multi-level aggregation. |

---

## 10. Historical Search

| Dimension | Assessment |
|---|---|
| **Exists** | **Partial** |
| **Location** | `src/storage/history_store.py`, `src/storage/workflow_history.py` |
| **Key Files** | `storage/history_store.py` (HistoryStore), `storage/workflow_history.py` (workflow_history_store), `storage/workflow_history.json` (on-disk storage) |
| **Maturity** | **Early** |
| **Gaps** | 1. History is stored as flat JSON files — no indexed search, no time-range queries, no full-text search. 2. No pagination or cursor-based retrieval. 3. No query filtering beyond workflow_id/run_id. 4. No efficient historical trend queries. 5. No database-backed history (SQLite is available but history uses JSON). 6. No history cleanup/retention policy. 7. No history export/archive capability. |
| **Recommended Improvements** | 1. Migrate history to SQLite or a proper database with indexed columns. 2. Add time-range query support. 3. Add cursor-based pagination. 4. Add trend analysis queries (price history over time). 5. Add retention policies and cleanup routines. 6. Add history export to CSV/Parquet. |

---

## 11. Customer Matching

| Dimension | Assessment |
|---|---|
| **Exists** | **Yes** |
| **Location** | `src/matching_runtime/` |
| **Key Files** | `services/matching_service.py` (MatchingService), `strategies/fuzzy_match_strategy.py`, `strategies/exact_match_strategy.py`, `strategies/normalized_match_strategy.py`, `strategies/historical_match_strategy.py`, `confidence/customer_confidence_calculator.py`, `normalization/text_normalizer.py`, `contracts/match_request.py`, `models/match_result.py`, `models/match_set.py` |
| **Maturity** | **Maturing** |
| **Gaps** | 1. No persistent matching results store (matches are in-memory). 2. No customer deduplication pipeline — matching runs but doesn't merge/consolidate. 3. Confidence scoring is rule-based, no ML-based scoring. 4. No match review workflow integration (ReviewRuntime is separate and not connected). 5. No batch matching performance optimization. 6. No match threshold configuration per task. 7. No blocking/keying strategy for large datasets. |
| **Recommended Improvements** | 1. Add persistent match result storage. 2. Integrate matching with entity resolution deduplication pipeline. 3. Add ML-based confidence scoring option. 4. Integrate with ReviewRuntime for human-in-the-loop matching. 5. Add blocking/keying for scaling to large datasets. 6. Add threshold tuning per match task. |

---

## 12. Product Matching

| Dimension | Assessment |
|---|---|
| **Exists** | **Yes** |
| **Location** | `src/matching_runtime/` |
| **Key Files** | `services/matching_service.py`, `strategies/fuzzy_match_strategy.py`, `strategies/exact_match_strategy.py`, `strategies/normalized_match_strategy.py`, `confidence/product_confidence_calculator.py`, `contracts/match_request.py`, `models/match_result.py`, `src/transform/comparison_engine.py` |
| **Maturity** | **Maturing** |
| **Gaps** | 1. Same gaps as Customer Matching (no persistent store, no ML scoring, no review workflow). 2. Product matching uses RapidFuzz for fuzzy matching — good but no support for custom tokenizers or domain-specific similarity. 3. No cross-source product merge/consolidation. 4. No product attribute-level matching (brand+model+size vs just name). 5. No duplicate product detection within a single source. |
| **Recommended Improvements** | 1. Same as Customer Matching improvements. 2. Add attribute-level matching (brand, model, size, variant). 3. Add within-source duplicate product detection. 4. Add cross-source product consolidation with golden record creation. 5. Add product attribute extraction pipeline integrated into matching. |

---

## 13. Master Data Management

| Dimension | Assessment |
|---|---|
| **Exists** | **Partial** |
| **Location** | `src/matching_runtime/repositories/master_data_repository.py`, `src/schema/` |
| **Key Files** | `matching_runtime/repositories/master_data_repository.py` (MasterDataRepository), `schema/canonical_product.py`, `schema/canonical_customer.py`, `schema/canonical_item.py`, `schema/canonical_order.py`, `src/canonical_products.json` |
| **Maturity** | **Prototype** |
| **Gaps** | 1. `MasterDataRepository` is an in-memory mock with no persistence. 2. No golden record management (creation, versioning, merging, retirement). 3. No golden record ID generation or cross-reference mapping. 4. No MDM governance (record ownership, stewardship, approval workflow). 5. No data quality rules for master records. 6. No MDM integration with entity resolution — they are separate systems. 7. Canonical schemas exist but are not populated from actual MDM processes. |
| **Recommended Improvements** | 1. Implement a persistent MDM store (SQLite or DB-backed). 2. Add golden record lifecycle (create, update, merge, retire, version). 3. Add cross-reference mapping (source IDs → golden record ID). 4. Add MDM governance with approval workflow. 5. Integrate MDM with entity resolution and matching. 6. Add data quality scoring for master records. 7. Add MDM reporting (golden record count, source coverage, quality metrics). |

---

## 14. Entity Resolution

| Dimension | Assessment |
|---|---|
| **Exists** | **Partial** |
| **Location** | `src/entity_runtime/` |
| **Key Files** | `engine.py`, `orchestration/orchestrator.py` (EntityOrchestrator), `extraction/extractor.py`, `normalization/normalizer.py`, `validation/validator.py`, `confidence/scorer.py`, `contracts/extracted_entity.py`, `contracts/entity_set.py`, `contracts/source_lineage.py`, `store/version_store.py`, `store/idempotency.py`, `concurrency/` (optimistic/pessimistic locking), `integration/workflow_adapter.py` |
| **Maturity** | **Early (pre-release)** |
| **Gaps** | 1. Entity resolution orchestration is implemented but appears to be pre-release/unreleased (no production usage evidence). 2. Confidence scoring is rule-based with no ML component. 3. No entity deduplication/merge logic — resolves entities but doesn't merge duplicates. 4. Entity resolution not integrated with matching runtime. 5. No entity survivorship rules (which attribute values to keep from which source). 6. No entity relationship management. 7. `entity_runtime/__init__.py` likely doesn't export the engine (separate pre-release package). |
| **Recommended Improvements** | 1. Complete entity resolution engine implementation and integration tests. 2. Add entity deduplication with merge/survivorship. 3. Integrate entity resolution with MatchingRuntime and MDM. 4. Add ML-based confidence scoring. 5. Add entity relationship extraction and management. 6. Add entity graph/timeline visualization. 7. Add entity resolution metrics (precision, recall, coverage). |

---

## 15. OCR

| Dimension | Assessment |
|---|---|
| **Exists** | **No** |
| **Location** | N/A |
| **Key Files** | `document_engine/loaders/pdf_loader.py` (uses PyMuPDF/fitz for text extraction — not OCR) |
| **Maturity** | **Not implemented** |
| **Gaps** | 1. No OCR capability exists in the repository. 2. `pdf_loader.py` does text extraction via PyMuPDF — this extracts embedded text, not scanned images. 3. No Tesseract, EasyOCR, or other OCR library integration. 4. No image preprocessing for OCR (skew correction, denoising, binarization). 5. No document image ingestion pipeline. 6. No OCR confidence scoring or post-processing. 7. No scanned PDF support. |
| **Recommended Improvements** | 1. Integrate Tesseract (via pytesseract) or EasyOCR for scanned document support. 2. Add image preprocessing pipeline (denoising, deskew, binarization). 3. Add OCR confidence scoring. 4. Add OCR post-processing (spelling correction, regex extraction). 5. Add support for scanned PDF (image-based) documents. 6. Add OCR metrics and quality reporting. |

---

## 16. Document Classification

| Dimension | Assessment |
|---|---|
| **Exists** | **Partial** |
| **Location** | `src/document_engine/classifiers/document_classifier.py` |
| **Key Files** | `document_engine/classifiers/document_classifier.py` (DocumentClassifier — keyword + structure based), `document_engine/parsers/section_detector.py`, `document_engine/parsers/table_parser.py` |
| **Maturity** | **Early** |
| **Gaps** | 1. Classification is keyword/structure-based only — no ML model. 2. No training data or model artifacts. 3. No configurable classification taxonomy. 4. No confidence scoring for classifications. 5. No multi-label classification. 6. No document type hierarchy. 7. Classification only works for structured/well-formatted documents. |
| **Recommended Improvements** | 1. Add ML-based document classification (e.g., scikit-learn or HuggingFace transformers). 2. Build training data collection pipeline. 3. Add configurable taxonomy/ontology. 4. Add classification confidence scoring. 5. Add multi-label classification support. 6. Add fallback to rule-based when ML confidence is low. 7. Add classification metrics (accuracy, precision, recall). |

---

## 17. Review Runtime

| Dimension | Assessment |
|---|---|
| **Exists** | **Yes** |
| **Location** | `src/review_runtime/` |
| **Key Files** | `services/review_service.py` (ReviewService), `services/feedback_service.py` (FeedbackService), `models/review_item.py`, `models/review_decision.py`, `models/review_correction.py`, `models/feedback_record.py`, `models/status.py`, `contracts/review_request.py`, `contracts/repository.py`, `repositories/in_memory_review_repository.py`, `repositories/in_memory_feedback_repository.py`, `tests/test_review_service.py` |
| **Maturity** | **Early** |
| **Gaps** | 1. In-memory only — no persistent storage for reviews or feedback. 2. Not integrated with any workflow stage (no auto-review triggers). 3. Not integrated with matching runtime for match review. 4. No UI (no review dashboard or queue). 5. No review assignment/routing logic. 6. No SLA tracking for pending reviews. 7. No audit trail for reviewer actions. 8. No batch review capability. |
| **Recommended Improvements** | 1. Add persistent review storage (SQLite or DB). 2. Integrate with matching runtime match results for review. 3. Integrate with entity resolution for entity review. 4. Add review queue with assignment and routing. 5. Add SLA tracking and escalation. 6. Add review audit trail. 7. Add batch review operations. 8. Build review dashboard UI. |

---

## 18. Monitoring

| Dimension | Assessment |
|---|---|
| **Exists** | **Yes** |
| **Location** | `src/telemetry/`, `src/integrations/supabase_client.py`, `src/core/logging/`, `src/status.py` |
| **Key Files** | `telemetry/telemetry_manager.py` (TelemetryManager — pipeline_runs, ingestion_logs, operational_alerts), `telemetry/pipeline_logger.py` (PipelineLogger), `integrations/supabase_client.py` (SupabaseClient), `core/logging/execution_logger.py` (ExecutionLogger), `src/scheduler.py` (WorkflowScheduler), `src/services/workflow_execution_service.py` (RunStatusStore), `src/dashboard.py` (Streamlit dashboard) |
| **Maturity** | **Maturing** |
| **Gaps** | 1. Telemetry relies on Supabase — no offline/fallback storage. 2. No real-time monitoring (no WebSocket, no streaming). 3. No alerting rules engine (alerts are workflow outputs, not system health alerts). 4. No metric aggregation (no Prometheus, Grafana, or statsd). 5. No distributed tracing. 6. No log aggregation/centralization. 7. Dashboard is Streamlit-based (no production monitoring UI). 8. No health check endpoints for internal components (only external connector health). |
| **Recommended Improvements** | 1. Add offline telemetry storage (SQLite fallback when Supabase unavailable). 2. Add real-time monitoring via WebSocket or polling-based status feed. 3. Add system health alert rules (connector failures, workflow timeouts, data quality degradation). 4. Add metric aggregation with Prometheus format. 5. Add structured logging with correlation IDs for distributed execution. 6. Upgrade dashboard to a production-grade monitoring UI. 7. Add internal component health checks. |

---

## 19. Workflow Versioning

| Dimension | Assessment |
|---|---|
| **Exists** | **Partial** |
| **Location** | `src/workflow_runtime/workspace/workspace_registry.py`, `workflows/*.json` |
| **Key Files** | `workspace/workspace_registry.py` (loads workflows from directories — implicit versioning via file paths), workflow JSON files (`workflows/quickmart_detergents_monitoring.json`, etc.) |
| **Maturity** | **Prototype** |
| **Gaps** | 1. No formal versioning schema — workflows are single files, overwritten on update. 2. No version history or rollback capability. 3. No migration between versions. 4. No compatibility checking between workflow versions. 5. No version tags or release management. 6. No canonical "active version" concept — the runner loads the current file. 7. No workflow diffing or comparison. |
| **Recommended Improvements** | 1. Add version field to `WorkflowDefinition` schema (semver format). 2. Add version history storage (append-only JSON or DB table). 3. Add rollback capability (load previous version). 4. Add compatibility checking between versions. 5. Add active/stable/beta version tags. 6. Add workflow diffing for version comparison. 7. Add workflow migration scripts for breaking changes. |

---

## 20. Workflow Testing

| Dimension | Assessment |
|---|---|
| **Exists** | **Partial** |
| **Location** | `tests/test_workflow_runtime.py`, `tests/locking/test_integration_workflow_runner.py`, `tests/locking/test_integration_crash_recovery.py`, `tests/locking/test_integration_concurrent.py`, `tests/locking/test_integration_idempotency.py`, `tests/test_main.py` |
| **Key Files** | `tests/test_workflow_runtime.py` (DSL parsing, validation, DAG construction, stage execution tests), `tests/locking/test_integration_workflow_runner.py` (end-to-end runner tests), `tests/locking/test_integration_crash_recovery.py` (crash resilience tests), `tests/locking/test_integration_concurrent.py` (concurrency tests) |
| **Maturity** | **Early** |
| **Gaps** | 1. No sandbox/test execution mode in the workflow runtime — tests execute real operations. 2. No mock data framework for workflow testing. 3. No fixture/test data generation for workflows. 4. No workflow contract testing (input/output schema validation). 5. No stage-level mocking utilities. 6. No workflow simulation/dry-run mode. 7. No performance/stress testing for workflow execution. 8. No workflow test coverage metrics. |
| **Recommended Improvements** | 1. Add sandbox/test execution mode with mock connectors and data. 2. Build test data generation utilities. 3. Add workflow contract tests (input/output schema). 4. Add stage-level mock framework. 5. Add dry-run mode that logs actions without side effects. 6. Add performance testing harness for workflows. 7. Add test coverage reporting for workflow definitions. |

---

## 21. Workflow Simulation

| Dimension | Assessment |
|---|---|
| **Exists** | **No** |
| **Location** | N/A |
| **Key Files** | None |
| **Maturity** | **Not implemented** |
| **Gaps** | 1. No workflow simulation or dry-run mode exists. 2. No what-if analysis capability. 3. No timeline simulation (simulate execution over time). 4. No cost estimation for workflow execution. 5. No data volume impact analysis. 6. No way to preview transformation/filter results before production execution. |
| **Recommended Improvements** | 1. Add dry-run/simulation mode to WorkflowRunner. 2. Add what-if analysis with configurable parameters. 3. Add timeline simulation for scheduled workflows. 4. Add execution cost estimation (API calls, scraping volume, compute). 5. Add data volume preview and impact analysis. 6. Add stage-level result preview in simulation mode. |

---

## Summary Matrix

| # | Capability | Exists | Maturity | Priority |
|---|---|---|---|---|
| 1 | Workflow Engine | Yes | Mature | — |
| 2 | Rule Engine | Partial | Early | Medium |
| 3 | Transformation Engine | Yes | Maturing | — |
| 4 | Regex Mapping | Partial | Low | Medium |
| 5 | Field Mapping | Partial | Early | Medium |
| 6 | Validation | Partial | Early | High |
| 7 | Filtering | Yes | Early | Low |
| 8 | Sorting | No | Not implemented | Low |
| 9 | Aggregation | No | Not implemented | Low |
| 10 | Historical Search | Partial | Early | Medium |
| 11 | Customer Matching | Yes | Maturing | — |
| 12 | Product Matching | Yes | Maturing | — |
| 13 | Master Data Management | Partial | Prototype | High |
| 14 | Entity Resolution | Partial | Early | High |
| 15 | OCR | No | Not implemented | Medium |
| 16 | Document Classification | Partial | Early | Medium |
| 17 | Review Runtime | Yes | Early | Medium |
| 18 | Monitoring | Yes | Maturing | — |
| 19 | Workflow Versioning | Partial | Prototype | Medium |
| 20 | Workflow Testing | Partial | Early | High |
| 21 | Workflow Simulation | No | Not implemented | Low |

**Legend:**  
Maturity: `Prototype` → `Early` → `Maturing` → `Mature`  
Priority: `High` = needs immediate investment, `Medium` = plan for next phase, `Low` = future consideration  
`—` = core capability already at acceptable maturity

---

## Recommended Immediate Actions (High Priority)

1. **Validation** — Build a production-grade data validation framework with configurable rules, error aggregation, and reporting. Current validation is scattered and incomplete.

2. **Entity Resolution** — Complete the entity resolution engine and integrate with MatchingRuntime. Entity resolution is pre-release with no production usage.

3. **Master Data Management** — Implement persistent MDM with golden record lifecycle, cross-reference mapping, and governance. MDM is currently an in-memory mock.

4. **Workflow Testing** — Add sandbox/testing mode, mock frameworks, and contract testing for workflows. Testing is currently limited to unit tests.

---

## Recommended Medium Priority Actions

5. **OCR** — Integrate Tesseract/EasyOCR for scanned document support. Currently only embedded PDF text extraction exists.

6. **Rule Engine** — Design and implement a declarative rule DSL with external configuration support.

7. **Field Mapping** — Build a declarative field mapping DSL with type coercion and transformation chaining.

8. **Historical Search** — Migrate history from JSON flat files to database-backed indexed storage with time-range queries.

9. **Review Runtime** — Add persistent storage and integrate with matching and entity resolution workflows.

10. **Workflow Versioning** — Add formal versioning with history, rollback, and compatibility checking.

---

## Recommended Improvements Summary per Capability

| Capability | Key Short-Term Fix | Key Medium-Term Improvement |
|---|---|---|
| Workflow Engine | Per-stage timeouts, cancellation | Parallel/conditional DAG branches |
| Rule Engine | External rule configuration | Declarative rule DSL |
| Transformation Engine | Deduplicate regex patterns | Streaming transformation |
| Regex Mapping | Centralized registry | External config |
| Field Mapping | Declarative mapping DSL | Visual mapping tool |
| Validation | Configurable validation rules | ML-based quality scoring |
| Filtering | Compound conditions | Chaining with metrics |
| Sorting | SortStage implementation | Multi-column sort |
| Aggregation | AggregationStage implementation | Time-series rollups |
| Historical Search | SQLite migration | Full-text search, trends |
| Customer Matching | Persistent match storage | ML-based confidence |
| Product Matching | Attribute-level matching | Cross-source consolidation |
| Master Data Management | Persistent golden record store | Governance workflows |
| Entity Resolution | Completion/integration | ML-based scoring |
| OCR | Tesseract integration | Image preprocessing |
| Document Classification | ML model integration | Training data pipeline |
| Review Runtime | Persistent storage | UI dashboard |
| Monitoring | Offline telemetry fallback | Real-time monitoring |
| Workflow Versioning | Formal version schema | Migration scripts |
| Workflow Testing | Sandbox mode | Contract testing |
| Workflow Simulation | Dry-run mode | What-if analysis |