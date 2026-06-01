 # PROJECT CONTEXT
 Date: 2026-06-01

 ## Purpose
 Provide a single onboarding document for future agents and developers to become productive without prior chat context.

 ## Ownership
 - Repository Owner: Benjamin Kamau
 - Repository Model: Single-owner repository

 ## Project Vision
 Build an operational intelligence platform for supplier and market price monitoring that enables automated data ingestion, normalization, matching, human review, and downstream execution (ERP, alerts, dashboards) with strong auditability and explainability.

 ## Platform Goal
 Operational Intelligence Platform

 Core capabilities:
 - Read
 - Understand
 - Match
 - Review
 - Decide
 - Execute
 - Learn

 ## Future Contributors
 - Copilot
 - ChatGPT
 - Cline
 - Codex
 - Human developers

 ## Runtime Roadmap
 - v0.1 Document Runtime
 - v0.2 Workflow Runtime
 - v0.3 Entity Runtime
 - v0.4 Matching Runtime
 - v0.5 Runtime Hardening
 - v0.6 Review Runtime
 - v0.7 ERP Runtime
 - v0.8 Agent Runtime

 ## Architecture Principles
 - Runtime isolation: enforce clear boundaries between runtimes and minimize synchronous coupling.
 - Immutable contracts: use versioned, explicit schemas for all public artifacts.
 - Deterministic processing first: deterministic logic and reproducible pipelines before introducing non-determinism.
 - AI augmentation later: design to allow AI agents and models to augment, not replace, deterministic core paths.
 - Auditability: every decision and change must be traceable and stored in an auditable trail.
 - Explainability: systems must export explainability metadata for matches and transformations.
 - Agent-switchability: support multiple agent implementations with consistent contracts and pluggable adapters.

 ## Major Decisions (summary)
 - Workflow Runtime v1: orchestrator-based scheduling and event-driven triggers. See ADRs for details.
 - Entity Runtime v1: canonical entity model with entity sets and change events as the source of truth.
 - Customer as Core Entity: products and suppliers model relate to `customer` as the primary tenant context.
 - No Party Abstraction in v1: simplified domain model to speed early delivery; party abstraction may be introduced later.
 - Historical Matching Strategy: append-only match proposals with review corrections applied as separate change events.

 ## Governance Rules
 The following artifacts and actions are required as part of project governance. These are enforced as part of the Definition of Done.
 - Architecture document
 - Implementation document
 - Summary document
 - Handoff document
 - ADR updates
 - Technical debt update
 - Roadmap update
 - Release notes
 - Git commit
 - Git push
 - Tag (milestone)

 ## Governance References
 - Branching Strategy and Release Tag Format are referenced in `agents/ETL_Platform_Governance.agent.md`.
 - Branching Strategy (defaults): `platform/intelligent-document-processing` (working branch), `feature/` (feature), `runtime/` (runtime), `hotfix/` (hotfix).
 - Release Tag Format (examples): `v0.4-matching-runtime`, `v0.5-runtime-hardening`, `v0.6-review-runtime`.

 ## Definition of Done
 The Definition of Done is definitive and includes the following required items. Work must not be considered complete until all applicable items are satisfied:
 - Code implemented
 - Unit tests passing
 - Integration tests passing
 - Regression tests passing
 - Architecture document created
 - Implementation document created
 - Summary document created
 - Handoff document created
 - ADRs updated
 - Runtime boundaries verified
 - Technical debt updated
 - Roadmap updated
 - Release notes created
 - Git commit completed
 - Git push completed
 - Milestone tag created when applicable
 - Future agent can continue from documentation alone

 ## Current Platform Status
 - Completed runtimes: Document Runtime (v0.1), Workflow Runtime (v0.2), Entity Runtime (v0.3), Matching Runtime (v0.4)
 - Current milestone: v0.4-matching-runtime released; next recommended milestone: v0.5-runtime-hardening

 ## Recommended Reading Order
 1. README.md
 2. ROADMAP.md
 3. PROJECT_CONTEXT.md
 4. PLATFORM_ARCHITECTURE_REVIEW.md
 5. ADRs
 6. Runtime Architecture Documents

 ## Agent-Switchability Rule
 All critical project knowledge must be persisted in repository documentation. No critical project knowledge should exist only in chat history.

 Future contributors may include:
 - GitHub Copilot
 - ChatGPT
 - Cline
 - Codex
 - Human developers

 ## Onboarding Notes for Agents
 - Locate high-level goals in `docs/ROADMAP.md` and `Readme.md`.
 - Use `docs/architecture/` for runtime and contract documentation.
 - Update the `focus_chain` or `/memories/repo/` with any new permanent facts learned during work.
 - When in doubt, open an ADR and record the decision before implementing.

 End of document.