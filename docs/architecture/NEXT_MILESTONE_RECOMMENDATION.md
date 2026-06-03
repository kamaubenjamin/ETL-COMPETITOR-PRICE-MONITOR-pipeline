# Next Milestone Recommendation — v0.5 Runtime Hardening

**Date**: 2026-06-03  
**Author**: Platform Architecture Review  
**Context**: Completed v0.5 deliverables — Contract Registry v1, CI Contract Validation v1, Runtime Boundary Verification v1 (Tier 1).  
**Purpose**: Evaluate and recommend the next implementation milestone among four candidates.

---

## Current Platform State

### Completed Milestones

| Milestone | Status | Key Deliverables |
|---|---|---|
| v0.1 Document Runtime | Done | Document ingestion pipeline, parsing, structure extraction |
| v0.2 Workflow Runtime | Done | Stage execution, dependency resolution, entity_extract support |
| v0.3 Entity Runtime | Done | Immutable contracts, normalization, confidence scoring |
| v0.4 Matching Runtime | Done | Exact/normalized/fuzzy/historical strategies, explainable scores |
| v0.5 Contract Registry v1 | Done | JSON Schema Draft 07 contracts, fixtures, validation |
| v0.5 CI Contract Validation v1 | Done | GitHub Actions workflow for contract tests and validation |
| v0.5 Runtime Boundary Verification v1 | Done | Tier 1 static import isolation (R01-R05, R12). 22 tests, COMPLIANT. 4 legacy exemptions |

### Outstanding Risks (from PLATFORM_ARCHITECTURE_REVIEW.md)

1. **Duplicate workflow execution** — Workflow Runtime lacks distributed locking
2. **Entity merge race conditions** — Concurrent updates can corrupt canonical records
3. **Manual threshold tuning** — Matching Runtime has no drift detection
4. **Limited observability** — Long-running workflows lack metrics and health visibility
5. **Incomplete audit linkage** — Review Runtime decisions not fully traceable to source artifacts

### Available Runtime Packages

```
src/workflow_runtime/     src/entity_runtime/       src/matching_runtime/
src/document_engine/      src/review_runtime/       src/api/
src/telemetry/            src/audit.py
```

---

## Candidate Evaluation

### Candidate 1: Workflow Runtime Locking

**Purpose**: Prevent duplicate or stale workflow execution through distributed locking or idempotency keys.

| Dimension | Assessment |
|---|---|
| **Dependencies** | Workflow Runtime only (`src/workflow_runtime/runtime/workflow_runner.py`, `src/workflow_runtime/contracts/execution_context.py`) |
| **Risks** | **Low** — well-understood pattern (file lock, DB row lock, or in-memory mutex). Risk of over-engineering if future architecture migrates to a distributed scheduler |
| **Architecture impact** | Moderate — adds lock acquisition/release to the workflow execution lifecycle. Affects `workflow_runner.py` and `execution_context.py` |
| **Effort estimate** | ~1 week (lock mechanism + integration tests + stale-lock recovery + audit logging) |
| **Business value** | Medium-High — prevents double-processing of supplier data, duplicate alerts, and incorrect aggregated reports downstream |
| **User-visible value** | Medium — fewer duplicate workflow runs; more predictable scheduled execution behaviour |
| **Technical debt reduction** | **High** — directly addresses "Lack of distributed locking; potential duplicate job execution" (PLATFORM_ARCHITECTURE_REVIEW.md) |
| **Score** | **9/10** — Smallest effort, highest risk reduction, completes v0.5 hardening arc |

### Candidate 2: Entity Runtime Concurrency Hardening

**Purpose**: Add transactional merge patterns or optimistic locking for entity_set updates to prevent data corruption under concurrent workflows.

| Dimension | Assessment |
|---|---|
| **Dependencies** | Entity Runtime (`src/entity_runtime/orchestration/`, `src/storage/history_store.py`). Benefits from locking patterns established in Candidate 1 |
| **Risks** | **Moderate** — concurrency fixes can introduce deadlocks or performance regressions without thorough stress testing |
| **Architecture impact** | Moderate — affects `entity_set` merging, `history_store` persistence, and normalization pipeline |
| **Effort estimate** | ~2 weeks (locking strategy design + migration plan + concurrency tests) |
| **Business value** | High — entity corruption from concurrent merges is a data-integrity risk with downstream impact on matching and reporting |
| **User-visible value** | Low — no visible feature change; prevents silent data corruption |
| **Technical debt reduction** | **High** — addresses "Race conditions on entity merges under concurrent updates" (PLATFORM_ARCHITECTURE_REVIEW.md) |
| **Score** | **6/10** — High value but larger effort; better sequenced after Workflow Runtime Locking establishes lock patterns |

### Candidate 3: Observability Foundation

**Purpose**: Add structured logging, execution metrics, health endpoints, and dashboards across all runtimes.

| Dimension | Assessment |
|---|---|
| **Dependencies** | All runtimes — cross-cutting by nature. Needs telemetry schema aligned with Monitoring Runtime (`src/telemetry/`) |
| **Risks** | **Medium** — scope creep risk. Instrumentation touches many files and requires consistent design decisions (logging library, metric format, dashboard tool) |
| **Architecture impact** | High — touches every runtime. Requires telemetry contract definition and Monitoring Runtime alignment |
| **Effort estimate** | ~3 weeks (design + instrumentation standards + per-runtime implementation + dashboards) |
| **Business value** | Medium — enables debugging, capacity planning, and SLA monitoring, but does not fix existing data-integrity defects |
| **User-visible value** | Low — ops team benefit only; no end-user feature change |
| **Technical debt reduction** | **Medium** — addresses "Limited observability and metrics around long-running workflows" |
| **Score** | **7/10** — Valuable foundation, but additive rather than corrective. Better sequenced after locking fixes |

### Candidate 4: Review Runtime

**Purpose**: Complete the interactive review layer with audit linking, UI integration tests, and atomic correction application.

| Dimension | Assessment |
|---|---|
| **Dependencies** | **Heavy** — depends on Matching Runtime (match proposals), Entity Runtime (corrections), Workflow Runtime (orchestration), API Runtime (endpoints), and a UI framework |
| **Risks** | **High** — largest scope, most unknowns. UI integration testing is immature. Audit linkage is incomplete. Correction propagation pipeline is undefined |
| **Architecture impact** | Very High — new interactive layer requires API contracts, UI state management, correction propagation pipeline, and event-driven feedback loops |
| **Effort estimate** | ~4-6 weeks (full runtime completion with UI, APIs, tests, audit) |
| **Business value** | High — enables human-in-the-loop quality assurance for production supplier matching |
| **User-visible value** | **High** — direct user-facing feature for operators/reviewers |
| **Technical debt reduction** | **Medium** — completes an unfinished runtime, but does not fix hardening gaps in existing runtimes |
| **Score** | **4/10** — Highest business value but premature without hardened foundation. Largest effort and risk |

---

## Priority Ranking

```
Rank  Candidate                          Score  Effort  Risk   Business Value  Debt Reduction
────  ─────────────────────────────────  ─────  ──────  ─────  ──────────────  ──────────────
1     Workflow Runtime Locking           9/10   1 wk    Low    Medium-High      High
2     Observability Foundation           7/10   3 wks   Med    Medium           Medium
3     Entity Runtime Concurrency         6/10   2 wks   Med    High             High
4     Review Runtime                     4/10   4-6 wks High   High             Medium
```

---

## Recommended Next Milestone

**`v0.5 Workflow Runtime Locking`**

### Why Now

1. **Directly follows the ROADMAP** — "Workflow Runtime Locking" is the next planned objective under v0.5 Runtime Hardening, immediately after "Runtime Boundary Verification"
2. **Smallest scope, fastest win** — Estimated 1 week vs 2-6 weeks for alternatives. Completes within the same hardening phase
3. **Unblocks downstream work** — Entity Runtime concurrency hardening can reuse the same lock primitives and patterns established here
4. **Addresses highest-risk item** — Duplicate workflow execution can corrupt supplier data, trigger false price alerts, and produce incorrect aggregated reports. This is a production-safety risk
5. **Completes v0.5 hardening trifecta** — Contract Registry (schema governance) + Boundary Verification (import isolation) + Workflow Locking (execution safety) form a complete foundation for subsequent phases

### Why Not The Others

**Entity Runtime Concurrency Hardening** — Better tackled after Workflow Runtime Locking establishes the locking infrastructure. Entity concurrency fixes may reuse the same lock primitives (e.g., `WorkflowExecutionLock` → `EntityMergeLock`), reducing duplicate design effort. Estimated 2 weeks vs 1 week — lower priority for the same hardening phase.

**Observability Foundation** — Valuable but additive. The platform has immediate data-integrity risks (duplicate runs, entity corruption) that observability does not fix. Observability helps debug problems after they occur; locking prevents them from occurring. Prevention first, diagnosis second.

**Review Runtime** — The most impactful for end-users but the largest effort and highest risk. Starting Review Runtime now would leave two hardening gaps (locking, observability) that it depends on. Review Runtime also requires stable Matching and Entity runtimes, which still have unaddressed concurrency and threshold-tuning risks.

---

## Prerequisites

1. **Lock mechanism decision** (choose one):
   - **Option A: In-memory mutex + process lock** — Simplest for single-process deployments. Risk: does not prevent duplicate execution across multiple worker processes
   - **Option B: File-based lock** — Cross-process, no external dependencies. Works for single-host deployments. `.lock` file in workspace directory
   - **Option C: Database-backed lock** — Row-level lock in history_store or shared DB. Required for multi-host deployments. Adds DB dependency
   - **Option D: Idempotency key** — Assign a unique execution ID per workflow run; reject duplicates at the runner level. Lightweight, no lock infrastructure needed
2. **Audit of current `workflow_runner.py`** — Identify all code paths that could lead to concurrent execution of the same workflow
3. **Test plan for concurrent execution scenarios** — Define scenarios: same workflow triggered twice, overlapping scheduled runs, manual + scheduled overlap, stale lock recovery

---

## Expected Deliverables

1. **Lock mechanism implementation** — Chosen option (file lock or idempotency key recommended for v0.5 simplicity)
2. **`WorkflowExecutionGuard` abstraction** — Reusable interface for preventing duplicate execution
3. **Integration tests** — Concurrent execution scenarios with verified prevention
4. **Stale lock recovery** — Timeout-based cleanup for crashed workflows
5. **Audit trail enhancement** — Lock acquisition/release events recorded in audit log
6. **Updated architecture documentation** — Locking strategy documented in `docs/architecture/`
7. **WORKFLOW_RUNTIME_LOCKING_V1_SUMMARY.md** — Implementation summary
8. **WORKFLOW_RUNTIME_LOCKING_V1_HANDOFF.md** — Handoff for next agent

---

## Definition of Done

- [ ] Lock/idempotency mechanism implemented and tested
- [ ] Concurrent execution prevention verified (pytest scenarios with overlapping triggers)
- [ ] Stale lock recovery tested (timeout + cleanup)
- [ ] Audit trail captures lock acquisition and release events
- [ ] `pytest tests/ -v` passes
- [ ] `python scripts/verify_boundaries.py` passes (no regressions)
- [ ] Architecture documentation updated in `docs/architecture/`
- [ ] `TECHNICAL_DEBT.md` updated — Workflow Runtime Locking item closed
- [ ] `docs/ROADMAP.md` updated — Workflow Runtime Locking marked complete
- [ ] Git commit and push completed
- [ ] Future agent can continue from repository documentation alone

---

## Recommended Milestone Name

**`v0.5-workflow-runtime-locking`**

---

## Appendix: Dependencies Between Candidates

```
Workflow Runtime Locking (1 wk)
  │
  ├──► Entity Runtime Concurrency (2 wks) — reuses lock patterns
  │
  └──► Observability Foundation (3 wks) — benefits from stable execution
         │
         └──► Review Runtime (4-6 wks) — requires hardened foundation
```

This ordering minimizes rework: lock first, then harden entity concurrency, then add observability, then build Review Runtime on a stable base.

---

## End of Recommendation