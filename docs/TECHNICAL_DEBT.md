# Technical Debt Register

This document tracks known limitations, deferred work, architectural compromises, and future improvements across the ETL Banking runtime stack. It is intended for future developers, agents, and maintainers.

## Document Runtime

### 1. Parsing Heuristics Are Limited
- Description: Document Runtime relies on rule-based parsing and heuristics rather than a full schema-aware parser.
- Impact: Complex or nonstandard document layouts may be misparsed, reducing downstream extraction accuracy.
- Priority: High
- Proposed Resolution: Add document-type-specific parsing patterns, a table schema mapper, or a more robust parser layer.
- Target Runtime: Document Runtime

### 2. Structural Extraction Is Not Fully Documented
- Description: The current architecture overview notes document ingestion and structure extraction, but detailed structural runtime behavior is not formalized.
- Impact: Future implementers may misinterpret boundaries between Document Runtime and Entity Runtime.
- Priority: Medium
- Proposed Resolution: Document structural extraction responsibilities explicitly in architecture docs and add workflow examples.
- Target Runtime: Document Runtime / Structural Runtime

### 3. Normalization Coverage Is Basic
- Description: Text normalization covers whitespace, label normalization, and currency canonicalization only.
- Impact: Variations in case, formatting, or locality-specific tokens may still produce inconsistent entity data.
- Priority: Medium
- Proposed Resolution: Expand normalization rules to include locale-aware formatting, unicode normalization, and canonical token mapping.
- Target Runtime: Document Runtime / Entity Runtime

### 4. Validation Coverage Is Limited
- Description: Entity validation currently checks for basic presence of entities, reference numbers, and financial totals.
- Impact: Missing or malformed entities may not be caught before workflow execution, increasing error risk.
- Priority: High
- Proposed Resolution: Add structured document schema validation, required field checks, and rules for common invoice/PO variants.
- Target Runtime: Validation Runtime / Entity Runtime

## Workflow Runtime

### 5. Stage Orchestration Is Minimal
- Description: Workflow Runtime supports stage registration, execution, and dependency resolution, but not advanced state management.
- Impact: Complex workflows with branching, error recovery, and stage retries are not yet fully supported.
- Priority: Medium
- Proposed Resolution: Add execution context tracking, retry policies, and richer stage lifecycle hooks.
- Target Runtime: Workflow Runtime

### 6. Contract Registry Enforcement Is Not Yet CI-Gated
- Description: Contract Registry v1 now standardizes core runtime artifact schemas, but validation is still local rather than enforced in hosted CI.
- Impact: Schema regressions can still merge if contributors do not run the local validation commands before committing.
- Priority: High
- Proposed Resolution: Add CI Contract Validation for `pytest tests/contracts -v`, `python scripts/validate_contracts.py`, compatibility checks against the released baseline, and ADR checks for MAJOR schema changes.
- Target Runtime: Workflow Runtime

### 7. No Review or Feedback Loop
- Description: Workflow Runtime currently lacks a review stage or mechanism to accept manual corrections and feed them back into matching.
- Impact: Low-confidence or incorrect matches cannot be corrected within the workflow, limiting production readiness.
- Priority: High
- Proposed Resolution: Implement `Review Runtime` as a workflow stage and define feedback loops for match corrections.
- Target Runtime: Review Runtime / Workflow Runtime

## Entity Runtime

### 8. Regex-Based Extraction
- Description: Entity Runtime extraction uses simple heuristics and regex-style logic rather than richer structured extraction.
- Impact: Complex line items, nested entities, and unusual invoice formats are harder to parse accurately.
- Priority: High
- Proposed Resolution: Add a table-to-entity mapper, document-type-specific extraction strategies, and structured extraction rules.
- Target Runtime: Entity Runtime

### 9. Basic Normalization
- Description: Entity Runtime normalization is deterministic but basic, focusing on whitespace and currency.
- Impact: Entity matching and downstream comparison may be degraded by inconsistent names or codes.
- Priority: Medium
- Proposed Resolution: Expand normalization to include synonyms, brand canonicalization, unit standardization, and product feature normalization.
- Target Runtime: Entity Runtime

### 10. Simple Confidence Scoring
- Description: The current Entity Runtime confidence model averages entity confidence values without domain-specific calibration.
- Impact: Confidence scores may not reflect real-world match reliability or downstream decision thresholds.
- Priority: Medium
- Proposed Resolution: Introduce entity-specific confidence calculators, per-entity scoring rules, and calibration based on validation results.
- Target Runtime: Entity Runtime

### 11. Limited Entity Validation
- Description: Validation checks are lightweight and do not enforce complete entity schemas.
- Impact: Some invalid or incomplete entities may reach the workflow, increasing error propagation.
- Priority: High
- Proposed Resolution: Add stronger entity schema validation, required field enforcement, and validation error reporting.
- Target Runtime: Entity Runtime

### 12. Future Entity Types Unspecified
- Description: Entity Runtime currently targets documents like invoices, purchase orders, and receipts, but does not define additional entity type support.
- Impact: Extending to new document types may require significant redesign.
- Priority: Low
- Proposed Resolution: Define a pluggable entity type registry and document-type extraction configuration.
- Target Runtime: Entity Runtime

## Matching Runtime

### 13. In-Memory Historical Matching Only
- Description: Historical matching is currently implemented as in-memory session state.
- Impact: Historical evidence is lost between workflow runs, limiting reuse and continuity.
- Priority: High
- Proposed Resolution: Add a persistent historical match store or append-only cache for workflow history.
- Target Runtime: Matching Runtime

### 14. No Persistence Layer
- Description: Matching Runtime does not include a durable persistence layer for candidate sources, match history, or audit logs.
- Impact: Runtime cannot reliably preserve state across executions or support long-term reconciliation.
- Priority: High
- Proposed Resolution: Implement pluggable data source adapters and persistence options for master data and historical records.
- Target Runtime: Matching Runtime / ERP Runtime

### 15. No Review Feedback Loop in Matching
- Description: Matching decisions are deterministic, but there is no mechanism to accept and incorporate manual review corrections.
- Impact: Incorrect matches cannot be improved via human feedback, reducing production readiness.
- Priority: High
- Proposed Resolution: Integrate review outcomes into matching strategy selection and historical match records.
- Target Runtime: Matching Runtime / Review Runtime

### 16. No ERP Synchronization or Data Source Integration
- Description: Matching Runtime currently assumes local or in-memory master data candidate sources only.
- Impact: It cannot integrate with ERP master data systems or support real ERP reconciliation workflows.
- Priority: High
- Proposed Resolution: Build ERP adapters, source configuration, and read-only synchronization support for ERP master data.
- Target Runtime: ERP Runtime / Matching Runtime

### 17. Strategy Coverage Is Limited
- Description: Matching supports exact, normalized, fuzzy, and historical strategies, but not semantic or embeddings-based matching.
- Impact: Hard-to-match product names and ambiguous customer/supplier records may still fail.
- Priority: Medium
- Proposed Resolution: Evaluate advanced matching strategies and introduce additional candidate selection heuristics as needed.
- Target Runtime: Matching Runtime

## Future Runtime Debt

### Review Runtime

#### 18. Review Stage Not Implemented
- Description: The review runtime layer is planned but not built.
- Impact: There is no workflow-native mechanism for exception handling, manual reconciliation, or audit-driven corrections.
- Priority: High
- Proposed Resolution: Define and implement a `Review Runtime` stage with review queues, manual override actions, and audit trails.
- Target Runtime: Review Runtime

#### 19. No Manual Correction Model
- Description: The platform lacks a model for tracking manual corrections, review decisions, or reviewer annotations.
- Impact: Human feedback cannot be persisted or replayed for future processing.
- Priority: Medium
- Proposed Resolution: Add review metadata models, correction contracts, and integration into the workflow artifact pipeline.
- Target Runtime: Review Runtime

### ERP Runtime

#### 20. ERP Integration Not Defined
- Description: ERP Runtime is planned but currently undefined beyond high-level roadmap goals.
- Impact: The project cannot yet support real ERP data reconciliation, lookups, or posting.
- Priority: High
- Proposed Resolution: Define ERP adapter interfaces, source configuration, and safe read-only access patterns.
- Target Runtime: ERP Runtime

#### 21. Credential and Security Handling Missing
- Description: No architecture exists yet for secure ERP credential management or service access.
- Impact: ERP integration may introduce security risks if done ad hoc.
- Priority: High
- Proposed Resolution: Design security and configuration boundaries for ERP connections, secrets, and access control.
- Target Runtime: ERP Runtime

### Agent Runtime

#### 22. Automation and Agent Orchestration Not Built
- Description: Agent Runtime is a planned future layer without implementation guidance.
- Impact: The platform cannot automate notifications, policy-driven actions, or agent workflows yet.
- Priority: Medium
- Proposed Resolution: Define the agent runtime contract, event triggers, and integration points with workflow outputs.
- Target Runtime: Agent Runtime

#### 23. No Policy or Governance Model for Agents
- Description: There is no defined governance model for automated agent behavior.
- Impact: Future agent actions may be inconsistent or unsafe without constraints.
- Priority: Medium
- Proposed Resolution: Establish agent governance rules, action approval processes, and audit logging requirements.
- Target Runtime: Agent Runtime

## Assumptions and Risks

### Assumptions
- Document Runtime output is sufficiently normalized for Entity Runtime extraction.
- Workflow Runtime will remain the orchestration kernel for runtime stages.
- Matching Runtime will use local or in-memory master data before ERP adapters are added.
- Review and agent capabilities are incremental extensions rather than immediate requirements.

### Risks
- Architectural drift if future runtimes are built without consistent runtime boundaries.
- Production readiness gaps due to missing review feedback, persistence, and ERP integration.
- Increased technical debt if existing Document/Entity assumptions are not reinforced with stronger validation.

## How to Maintain This Register
- Add new debt items as the architecture evolves.
- Update priority and resolution plans when milestones complete.
- Link runtime-specific issues to the corresponding architecture documents.
- Use this register as a living guide for roadmap and release planning.

## Additional Debt Notes

### Deferred Work
- **Description:** Architectural work remains for Review Runtime, API Runtime, Monitoring Runtime, ERP Runtime, and Agent Runtime.
- **Impact:** The platform cannot yet support review feedback, external integration, observability, or automation runtimes.
- **Priority:** High
- **Proposed Resolution:** Prioritize architecture and implementation of Review, API, Monitoring, ERP, and Agent runtimes.
- **Target Runtime:** Review Runtime, API Runtime, Monitoring Runtime, ERP Runtime, Agent Runtime

### Known Limitations
- **Description:** Existing design includes heuristic parsing, basic normalization, and lightweight validation.
- **Impact:** Production readiness is limited by inconsistent document handling and match reliability.
- **Priority:** High
- **Proposed Resolution:** Strengthen validation, normalization, and parser adaptability for broader document coverage.
- **Target Runtime:** Document Runtime, Entity Runtime

### Persistence Gaps
- **Description:** There is no durable persistence layer for match history, audit logs, or long-lived runtime state in the current architecture.
- **Impact:** State is lost between executions and long-term reconciliation is restricted.
- **Priority:** High
- **Proposed Resolution:** Define persistence adapters for historical matching, audit trails, and master data state.
- **Target Runtime:** Matching Runtime, ERP Runtime

### Scalability Concerns
- **Description:** Workflow orchestration and matching candidate generation are not yet designed for high-volume parallel workloads.
- **Impact:** The platform may struggle to scale to large document batches or high throughput.
- **Priority:** Medium
- **Proposed Resolution:** Add batching, throttling, and orchestration scaling strategies in Workflow and Matching runtimes.
- **Target Runtime:** Workflow Runtime, Matching Runtime

### Review Workflow Limitations
- **Description:** Review workflow and human feedback capture are currently architectural concepts, not implemented runtime behavior.
- **Impact:** There is no formal feedback loop to correct and improve matching outcomes.
- **Priority:** High
- **Proposed Resolution:** Implement Review Runtime, feedback capture, and correction lifecycle processing.
- **Target Runtime:** Review Runtime
