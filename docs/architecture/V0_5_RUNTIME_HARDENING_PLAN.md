# V0.5 Runtime Hardening Plan
Date: 2026-06-01

Purpose
-------
Translate findings from `PLATFORM_ARCHITECTURE_REVIEW.md` into a concrete implementation plan for the v0.5 Runtime Hardening milestone. This plan focuses on contractual stability, boundary verification, concurrency hardening, observability, and review-audit integrity.

Scope / Focus Areas
-------------------
1. Contract Registry
2. Contract Validation Tests
3. Runtime Boundary Verification
4. Entity Runtime Concurrency Hardening
5. Workflow Runtime Locking
6. Matching Benchmark Framework
7. Observability Improvements
8. Review Runtime Audit Linking

For each focus area the plan lists: problem statement, architecture impact, implementation approach, affected runtimes, risks, and an effort estimate.

---

1. Contract Registry

- Problem statement
  - Contracts (extraction JSON, entity schema, match result schema) are informal and unversioned; inconsistencies cause silent downstream breakage.

- Architecture impact
  - Central registry enables schema discovery, versioning and CI-driven contract validation. It reduces coupling risk and makes backward-compatibility explicit.

- Implementation approach
  - Adopt a lightweight JSON Schema registry (self-hosted or schema-repo) and add conventions for schema naming and semantic versioning.
  - Place canonical schemas under `docs/contracts/` and automate publishing to the registry.
  - Create minimal registry API / README and migration guidelines.

- Affected runtimes
  - Document, Entity, Matching, Workflow

- Risks
  - Up-front effort to convert existing artifacts to schemas; consumers may need minor changes.
  - Choice of registry tech can create lock-in; mitigate by using open formats (JSON Schema, OpenAPI).

- Effort estimate
  - Medium — 3 person-weeks (schema inventory, registry setup, initial schemas, docs)

---

2. Contract Validation Tests

- Problem statement
  - No centralized contract test suite; incompatible changes pass CI unnoticed.

- Architecture impact
  - CI contract tests will gate deployments and enforce backward-compatible changes across runtimes.

- Implementation approach
  - Implement a contract-test harness that validates produced artifacts against registry schemas (unit fixtures + integration smoke tests).
  - Add CI job(s) to run contract validation on PRs and on release pipelines.

- Affected runtimes
  - Document, Entity, Matching, Review

- Risks
  - Initial false-positives from incomplete schema coverage; require iterative refinement.

- Effort estimate
  - Medium — 2 person-weeks (harness, sample tests, CI integration)

---

3. Runtime Boundary Verification

- Problem statement
  - Some components assume synchronous interactions; runtime boundaries are insufficiently enforced.

- Architecture impact
  - A verification toolset and runbook will make asynchronous, event-driven contracts the default, reducing tight coupling.

- Implementation approach
  - Define a boundary verification checklist and automated smoke-tests that assert only allowed interactions (e.g., event topics, read-only queries) between runtimes.
  - Add contract-test scenarios that exercise boundary constraints.

- Affected runtimes
  - All runtimes (Document, Workflow, Entity, Matching, Review, ERP)

- Risks
  - The verification may flag valid but legacy synchronous flows; plan a remediation path and exemptions via ADR.

- Effort estimate
  - Medium — 2 person-weeks (checklist, automated checks, runbook)

---

4. Entity Runtime Concurrency Hardening

- Problem statement
  - Race conditions observed for concurrent entity merges and updates leading to potential entity corruption.

- Architecture impact
  - Requires clarifying ownership of persistent stores, introducing locking or compare-and-swap merging, and migration strategies for existing entity sets.

- Implementation approach
  - Evaluate patterns: optimistic locking (versioned entities), compare-and-apply merges, or short distributed locks around merge operations.
  - Prototype optimistic merge with strong audit trail and reconciliation job to detect / repair anomalies.
  - Add migration guidance and tests to cover concurrent update scenarios.

- Affected runtimes
  - Entity Runtime primarily; Workflow and Matching as upstream callers

- Risks
  - High complexity; possible performance impacts; requires thorough testing and rollback paths.

- Effort estimate
  - High — 6 person-weeks (design, prototype, tests, rollout plan)

---

5. Workflow Runtime Locking

- Problem statement
  - Lack of distributed locking leads to duplicate job execution and inconsistent state under failures.

- Architecture impact
  - Introducing distributed locks or leader-election ensures idempotent job execution and predictable retry behavior.

- Implementation approach
  - Integrate a lightweight locking backend (Redis, DynamoDB, or DB-based advisory locks) for job acquisition.
  - Add idempotency keys, improve retry policy, and document failure modes.
  - Provide a migration plan for existing scheduled jobs.

- Affected runtimes
  - Workflow Runtime; affects all runtimes triggered by orchestrator

- Risks
  - Operational overhead of lock infrastructure; need to ensure high availability of locking store.

- Effort estimate
  - Medium — 3 person-weeks (integration, tests, runbook)

---

6. Matching Benchmark Framework

- Problem statement
  - Matching thresholds are tuned manually; no benchmark dataset or automated drift detection.

- Architecture impact
  - A repeatable benchmark and evaluation harness allows automated threshold tuning and regression detection.

- Implementation approach
  - Curate representative benchmark datasets (sample of historical extractions + ground-truth match labels).
  - Build an evaluation harness (batch runner) to compute metrics (precision, recall, F1, ROC) and track over time.
  - Add CI job to run benchmark on model/config changes and report drift.

- Affected runtimes
  - Matching Runtime; dependent on Entity normalization outputs

- Risks
  - Data privacy concerns for production data in benchmark sets — ensure anonymization or synthetic datasets.

- Effort estimate
  - Medium — 3 person-weeks (dataset curation, harness, reporting)

---

7. Observability Improvements

- Problem statement
  - Limited metrics, tracing, and alerts slow down incident response and capacity planning.

- Architecture impact
  - Instrumentation across runtimes (metrics, logs, traces) enables SLOs, alerting, and faster root-cause analysis.

- Implementation approach
  - Define a metrics & tracing plan: required counters, histograms, and span conventions for each runtime.
  - Instrument critical code paths, add dashboards (Grafana) and basic alert rules (error rate, latency, queue depth).
  - Ship metrics to a central observability backend and document runbook for common incidents.

- Affected runtimes
  - All runtimes; focus first on Workflow, Entity and Matching

- Risks
  - Cost of observability infrastructure and potential PII leakage in logs; require scrubbing policies.

- Effort estimate
  - Medium — 3 person-weeks (instrumentation, dashboards, alerts)

---

8. Review Runtime Audit Linking

- Problem statement
  - Review actions are not consistently linked to original artifacts; corrections can be lost or orphaned.

- Architecture impact
  - Requires stronger audit model and atomic application of review corrections to avoid conflicting state.

- Implementation approach
  - Define and enforce review event schema with explicit lineage fields (artifact id, match id, reviewer id, timestamp).
  - Make review correction application transactional where possible, or emit compensating events and reconciliation jobs.
  - Add test coverage and CI checks for review workflows.

- Affected runtimes
  - Review Runtime; Entity Runtime (consumer of corrections); Workflow Runtime (orchestrator)

- Risks
  - Complexity around transactional semantics across distributed services; reconcile via append-only corrections and reconciliation jobs.

- Effort estimate
  - Medium — 2 person-weeks (schema, runbook, tests)

---

# Milestone Scope

This milestone focuses on platform hardening: contract governance, runtime boundary enforcement, concurrency and locking improvements, benchmarking for matching, and observability. The work is intentionally non-functional (documentation, tests, harnesses) plus targeted implementation patterns (locking, optimistic merges) that are low-impact to existing API shapes.

# Deliverables

- `docs/contracts/` schema set and registry README
- Contract validation harness and CI jobs
- Boundary verification checklist and automated checks
- Entity merge concurrency prototype and migration plan
- Workflow runtime locking integration plan and tests
- Matching benchmark dataset and evaluation harness
- Observability dashboards and alert rules
- Review runtime audit schema and reconciliation runbook
- ADRs for any design decisions or exemptions

# Documentation Requirements

- Architecture document for each implemented change (link to ADR)
- Implementation document with run/runbook and rollback steps
- Summary document for stakeholders
- Handoff document for operations
- Technical debt register updates

# Testing Requirements

- Unit tests for any new logic
- Integration tests exercising contract validation and boundary checks
- Regression benchmark runs for matching
- Load/soak tests where locking or concurrency changes could affect throughput

# Definition of Done

Work is complete when:
- Implementation (or documentation + RFC) exists
- Unit, integration, and regression tests added and passing
- Contract validations run in CI with passing results
- ADRs and architecture docs created/updated
- Runbooks and handoff docs published
- Observability dashboards and basic alerts deployed
- Migration or rollout plan documented with rollback strategy
- Release notes and milestone tag created

# Recommended Implementation Order

1. Contract Registry (foundation)
2. Contract Validation Tests (CI gating)
3. Runtime Boundary Verification (enforce contracts)
4. Workflow Runtime Locking (reduce duplicate execution)
5. Entity Runtime Concurrency Hardening (merge safety)
6. Matching Benchmark Framework (metrics + drift detection)
7. Observability Improvements (monitoring & alerts)
8. Review Runtime Audit Linking (finalize audit integrity)

# Risks

- Migration friction: schema changes can require multiple runtime updates.
- Operational overhead: new infra (locks, observability) increases ops burden.
- Data privacy: benchmark datasets must be anonymized.
- Performance regressions from locking or optimistic strategies — mitigate via canary and load tests.

# Success Metrics

- Contract coverage: % of public artifacts validated by schema (> 90%)
- Contract test pass rate on CI (100% on gated branches)
- Reduction in cross-runtime incidents attributable to contract/boundary violations (target: -80%)
- Reduction in duplicate workflow executions (target: -90%)
- Matching metrics stable or improved on benchmark (precision/recall change within tolerance)
- Mean time to detect/resolve incidents (MTTD/MTTR) improved by 50% with observability

# Release Plan

Phased rollout pattern:
1. Implement and test in feature branches and CI.
2. Deploy components to a staging environment with contract validation enabled.
3. Run benchmark and regression suites; run reconciliation jobs where necessary.
4. Canary deploy to subset of production traffic (or controlled dataset) and monitor metrics.
5. Full rollout with monitoring and rollback plan in place.

---

# Effort Estimate (summary)

- Contract Registry: 3 person-weeks
- Contract Validation Tests: 2 person-weeks
- Runtime Boundary Verification: 2 person-weeks
- Entity Runtime Concurrency Hardening: 6 person-weeks
- Workflow Runtime Locking: 3 person-weeks
- Matching Benchmark Framework: 3 person-weeks
- Observability Improvements: 3 person-weeks
- Review Runtime Audit Linking: 2 person-weeks

Total: 24 person-weeks (approx). With parallel staffing (2–3 engineers), target calendar duration: 6–10 weeks depending on scope and parallelization.

# Recommended First Implementation Task

Start with the **Contract Registry**: inventory schemas, publish canonical schemas to `docs/contracts/`, and add a minimal contract validation CI job. This reduces risk for subsequent work and enables CI gating.

---

End of plan.
