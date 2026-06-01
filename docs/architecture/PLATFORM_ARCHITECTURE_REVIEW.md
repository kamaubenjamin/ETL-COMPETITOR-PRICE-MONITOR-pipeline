 # PLATFORM ARCHITECTURE REVIEW — v0.4-matching-runtime
 Date: 2026-06-01

 ## Context
 - Release: v0.4-matching-runtime (matching runtime released)
 - Completed milestones: v0.1 Document Runtime; v0.2 Workflow Runtime; v0.3 Entity Runtime; v0.4 Matching Runtime
 - Purpose: Repository governance and runtime boundary verification for the platform.

 ## Scope
 This document reviews the following runtimes:
 1. Document Runtime
 2. Workflow Runtime
 3. Entity Runtime
 4. Matching Runtime
 5. Review Runtime

 ---

 ## Runtime Reviews

 ### Document Runtime
 - Purpose: Ingest and structurally extract information from raw supplier artifacts (PDF, CSV, HTML) into the platform's canonical extraction format.
 - Responsibilities:
   - Document ingestion (file pickup, polling, connectors)
   - OCR / parsing / heuristics to extract structured fields
   - Produce `extracted_entity` and `source_lineage` artifacts
   - Validate & forward outputs to normalization and entity pipelines
 - Inputs:
   - Raw documents (PDF, CSV, HTML), supplier metadata, ingestion config
 - Outputs:
   - Structured extraction JSON (line items, totals, supplier refs), lineage metadata
 - Public Contracts:
   - Extraction JSON schema (extracted_entity, line_item, document_reference, document_financials)
   - Topic / file path contract for downstream consumers (e.g., `extraction.<source>.v1`)
 - Dependencies:
   - Normalization and confidence scoring services
   - `src/transform` normalization helpers (e.g., product normalizer)
   - Audit logger and storage
 - Runtime Boundaries:
   - Stateless extraction workers; side-effects limited to emitting well-typed extraction artifacts and audit events
 - Known Technical Debt:
   - No formal schema versioning; ad-hoc field names
   - OCR edge-case coverage is limited (multi-column tables, multi-currency)
   - Limited E2E contract tests between extractor and normalizer

 ### Workflow Runtime
 - Purpose: Orchestrate ETL pipelines, scheduling, retries, and cross-stage coordination.
 - Responsibilities:
   - Schedule workflows, trigger ingestion and downstream stages
   - Record workflow state and job lifecycle in the audit trail
   - Provide APIs for starting/stopping workflows and inspecting history
 - Inputs:
   - Workflow definitions (`WorkflowConfig`), source configs, external triggers
 - Outputs:
   - Task events, job status updates, audit records, failure alerts
 - Public Contracts:
   - Workflow config schema and job status event schema
 - Dependencies:
   - Task runners/workers, audit logger, storage/history store, notification subsystem
 - Runtime Boundaries:
   - Orchestrator should not perform heavy extraction/matching work — it delegates to workers
 - Known Technical Debt:
   - Lack of distributed locking; potential duplicate job execution
   - Limited observability and metrics around long-running workflows

 ### Entity Runtime
 - Purpose: Manage canonical entity lifecycle (products, suppliers, customers), identity resolution and versioned entity sets.
 - Responsibilities:
   - Normalize and canonicalize entities
   - Merge/deduplicate entities and manage `entity_set` records
   - Emit entity-change events for downstream consumers
 - Inputs:
   - Extracted entities, normalized attributes, match decisions
 - Outputs:
   - Canonical entity records, entity sets, change events
 - Public Contracts:
   - Canonical entity schema, entity change event contract, normalization API
 - Dependencies:
   - Normalization library, confidence scoring, persistence layer (history_store)
 - Runtime Boundaries:
   - Persistent store ownership and consistency guarantees must be explicit (optimistic vs transactional)
 - Known Technical Debt:
   - Race conditions on entity merges under concurrent updates
   - No consistent migration story for evolving entity schemas

 ### Matching Runtime
 - Purpose: Compute similarity and link records across sources into canonical identities (product linking).
 - Responsibilities:
   - Feature extraction for matching (brand, size, category, tokens)
   - Apply fuzzy matching, thresholding and tie-breaking rules
   - Provide explainability data (match features, scores)
 - Inputs:
   - Normalized product features, canonical product index, threshold configs
 - Outputs:
   - Match results (candidate pairs, scores, canonical assignments), match audit
 - Public Contracts:
   - `match_products` result schema, threshold and configuration contract
 - Dependencies:
   - `src/transform/comparison_engine.py`, normalization, feature store or index, ML models (if present)
 - Runtime Boundaries:
   - Matching must be a read-only consumer of canonical store (no direct mutations); decisions are proposals applied by Entity Runtime
 - Known Technical Debt:
   - Thresholds tuned manually; no automated drift detection
   - Limited test coverage for adversarial and low-signal cases

 ### Review Runtime
 - Purpose: Human-in-the-loop quality assurance and correction workflow for matches and extractions.
 - Responsibilities:
   - Surface candidate matches and extraction anomalies to reviewers
   - Capture accept/reject decisions and propagate corrections downstream
 - Inputs:
   - Match results, extraction artifacts, QC rule triggers
 - Outputs:
   - Review decisions, corrected entities, audit trail entries
 - Public Contracts:
   - Review event schema, UI back-end API contract for accepting corrections
 - Dependencies:
   - Matching Runtime, Entity Runtime, Audit and storage, Notification system
 - Runtime Boundaries:
   - Review is an interactive layer; persistence of decisions must be atomic to avoid lost corrections
 - Known Technical Debt:
   - Review UI and APIs lack robust integration tests
   - Audit linkage between review actions and original artifacts is incomplete

 ---

 ## Runtime Dependency Map
 High-level event-driven flow:
 - Document Runtime -> (extracted_entity) -> Entity Runtime -> (canonical entities) -> Matching Runtime -> (match proposals) -> Entity Runtime
 - Workflow Runtime orchestrates and triggers Document/Matching/Entity stages
 - Review Runtime consumes match proposals and sends corrections back into Entity Runtime

 ```mermaid
 graph TD
   Document[Document Runtime] -->|extracted_entity| Entity[Entity Runtime]
   Entity -->|canonical_index| Matching[Matching Runtime]
   Matching -->|match_proposals| Review[Review Runtime]
   Review -->|corrections| Entity
   Workflow[Workflow Runtime] --> Document
   Workflow --> Matching
   Workflow --> Entity
 ```

 ---

 ## Boundary Compliance Review
 Findings:
 - Separation of concerns is mostly enforced by the event-driven flow; however, several services assume synchronous calls which risks tight coupling.
 - Orchestrator occasionally performs work better suited to workers; this blurs runtime boundaries.
 - Recommendation: enforce strict async contracts and add a contract-test suite to block cross-boundary regressions.

 ---

 ## Contract Consistency Review
 Findings:
 - Several important contracts (extraction JSON, entity schema, match result schema) exist informally but are not recorded in a central schema registry.
 - Naming and versioning for contracts are inconsistent across the codebase.
 - Recommendation: adopt a schema registry (JSON Schema, Avro or OpenAPI for HTTP endpoints) and enforce versioned contracts with CI contract tests.

 ---

 ## Circular Dependency Analysis
 Findings:
 - No hard runtime-level circular code imports were observed in scope of this review; logical feedback loops exist (Review -> Entity -> Matching -> Review) but are event-driven and acceptable if implemented as append-only events.
 - Risk: synchronous RPCs between Matching and Entity could create tight runtime cycles. Avoid bi-directional RPCs; prefer event-driven acknowledgements.

 ---

 ## Documentation Coverage Review
 Findings:
 - High-level ADRs and architecture notes exist in `docs/` but contract and runtime boundary docs are incomplete.
 - Missing items: formal JSON schemas, message/topic catalog, contract testing instructions, and runtime SLAs.
 - Recommendation: expand docs with a `docs/contracts/` folder and a `docs/runtimes/` subfolder with per-runtime runbooks.

 ---

 ## Technical Debt Summary
 - No schema registry or contract tests.
 - Manual threshold tuning and lack of benchmark datasets for matching.
 - Race conditions in entity merges.
 - Limited observability and distributed locking mechanism for orchestrated jobs.

 ---

 ## Review Runtime Readiness Assessment
 Scoring (Green/Yellow/Red) and rationale:
 - Document Runtime: Yellow — core extraction flows exist; needs schema versioning and E2E contract tests.
 - Workflow Runtime: Yellow — functional but needs distributed locks and better observability.
 - Entity Runtime: Yellow — working but concurrency and migrations are risky.
 - Matching Runtime: Green (Limited) — v0.4 released; suitable for controlled traffic with monitoring and threshold tuning.
 - Review Runtime: Red — interactive review tooling and audit linking need completion before broad rollout.

 ---

 ## ERP Runtime Readiness Assessment
 (ERP = Enterprise Resource Planning integration readiness)
 - Current state: Low readiness for direct ERP integration.
 - Gaps:
   - No secure, idempotent connector contract for ERP systems
   - Transactional guarantees absent for pushing corrected canonical records
 - Recommendation: provision a connector spec, add idempotency keys, and define failure semantics before ERP integration.

 ---

 ## Recommendations
 1. Implement a central schema/contract registry and add contract tests to CI.
 2. Harden Entity Runtime: add transactional merge patterns or optimistic locking and migration tooling.
 3. Make Matching Runtime reproducible: add benchmark datasets, automated threshold testing, and drift monitoring.
 4. Improve Workflow Runtime: add distributed locking, stronger observability, and a job retry policy.
 5. Complete Review Runtime: full audit linkage, stronger UI integration tests, and atomic correction application.
 6. Create a release checklist for runtime boundary verification and a gating process for major releases.

 ---

 ## Risks
 - Incorrect matches propagating to ERP or billing systems
 - Data drift leading to silent matching degradation
 - Concurrent merges causing entity corruption
 - Poor observability delaying incident response

 ---

 ## Next Milestone
 - Suggested milestone: `v0.5-runtime-hardening`
 - Key deliverables:
   1. Contract registry + contract CI tests
   2. Distributed locking for Workflow Runtime
   3. Entity merge concurrency fixes + schema migration plan
   4. Matching benchmark dataset + automated threshold tuning job
   5. Review Runtime audit linking improvements

 ---

 ## Appendix
 - Related code areas to inspect when implementing recommendations:
   - `src/workflows.py` (workflow definitions and runner)
   - `src/transform/product_normalizer.py` (normalization helpers)
   - `src/transform/comparison_engine.py` (matching engine)
   - `src/audit.py` (audit and logging)
   - `src/storage/history_store.py` (persistence and historical snapshots)

 End of review.