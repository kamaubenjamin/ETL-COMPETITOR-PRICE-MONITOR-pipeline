# Runtime Boundary Map
Date: 2026-06-01

## Purpose
Formalise the allowed and disallowed interaction surfaces between every pair of platform runtimes. This document supersedes the informal boundary descriptions in `RUNTIME_BOUNDARIES.md` with a machine-readable dependency matrix, verifiable compliance rules, a legacy exemption process, and a verification strategy for CI enforcement.

---

## Runtime Dependency Matrix

| Producer \\ Consumer | Document | Workflow | Entity | Matching | Review | API | Monitoring |
|---|---|---|---|---|---|---|---|
| **Document** | — | → (events) | → (extracted_entity) | ✗ | ✗ | ✗ | → (observability) |
| **Workflow** | → (triggers) | — | → (triggers) | → (triggers) | → (triggers) | ↔ (requests) | → (observability) |
| **Entity** | ← (reads) | → (entity_set) | — | → (canonical_index) | ✗ | ✗ | → (observability) |
| **Matching** | ✗ | → (match_results) | ↛ (read-only queries only) | — | → (match_proposals) | ✗ | → (observability) |
| **Review** | ✗ | → (review_decisions) | → (corrections) | ← (reads proposals) | — | ✗ | → (observability) |
| **API** | ✗ | → (delegates) | ✗ | ✗ | ✗ | — | → (observability) |
| **Monitoring** | ← (reads) | ← (reads) | ← (reads) | ← (reads) | ← (reads) | ← (reads) | — |

### Legend
| Symbol | Meaning |
|---|---|
| — | Self (not a cross-runtime interaction) |
| → | Event / data push (producer emits; consumer subscribes) |
| ↔ | Request / response (synchronous or asynchronous, allowed) |
| ↛ | Read-only query (no mutation allowed) |
| ← | Read / observe only (no control flow) |
| ✗ | Disallowed (must not exist in any form) |

---

## Interaction Protocols

### 1. Event-Driven Data Flow (→)
- Producer emits a well-typed artifact to a topic, queue, or shared location.
- Consumer subscribes and processes asynchronously.
- The artifact must conform to a Contract Registry schema.
- Producer must not wait synchronously for consumer processing (except via explicit Workflow Runtime orchestration).

### 2. Synchronous Request/Response (↔)
- Only permitted where explicitly listed.
- Must be mediated by the Workflow Runtime or API Runtime.
- Must have a registered ADR exemption if cross-runtime and synchronous.

### 3. Read-Only Queries (↛)
- Matching Runtime may query Entity Runtime canonical stores for candidate lookups.
- Must not write, lock, or modify state in the queried runtime.
- Must use a read-only interface (no side effects).

### 4. Observability Reads (←)
- Monitoring Runtime may read metrics, logs, and traces from any runtime.
- Must not inject control-flow directives, configuration overrides, or execution commands.

---

## Boundary Compliance Rules

Each rule is assigned a unique identifier (R01–R12) for traceability.

### Import Isolation Rules

**R01 — Document Runtime Must Not Import Entity, Matching, or Review Runtimes**
- Rationale: Document Runtime is a pure ingestion layer. It must not have compile-time or runtime dependencies on higher-level runtime modules.
- Verification: Static import analysis — assert that `src/extract/`, `src/document_engine/` modules do not import from `src/entity_runtime/`, `src/matching_runtime/`, `src/review_runtime/`.

**R02 — Entity Runtime Must Not Import Matching or Review Runtimes**
- Rationale: Entity Runtime produces the canonical index that Matching consumes. Reverse dependency creates a cycle.
- Verification: Static import analysis — assert that `src/entity_runtime/` modules do not import from `src/matching_runtime/`, `src/review_runtime/`.

**R03 — Matching Runtime Must Not Import Document Runtime**
- Rationale: Matching operates on normalized entities, not raw documents.
- Verification: Static import analysis — assert that `src/matching_runtime/` modules do not import from `src/extract/`, `src/document_engine/`.

**R04 — Review Runtime Must Not Import Document or Entity Runtimes**
- Rationale: Review operates on match proposals and correction events, not raw documents or entity internals.
- Verification: Static import analysis — assert that `src/review_runtime/` modules do not import from `src/extract/`, `src/document_engine/`, `src/entity_runtime/`.

**R05 — API Runtime Must Only Import Workflow Runtime**
- Rationale: API Runtime is a thin gateway. It must not couple to internal runtime internals.
- Verification: Static import analysis — assert that `src/api/` modules import only from `src/workflow_runtime/` and shared utilities.

### Contract Adherence Rules

**R06 — All Cross-Runtime Data Exchange Must Use a Contract Registry Schema**
- Rationale: Without schema enforcement, incompatible changes pass CI undetected.
- Verification: Integration test — assert that every artifact emitted at a boundary validates against its registered JSON Schema in `docs/contracts/`.

**R07 — Review Runtime Corrections Must Be Append-Only Events**
- Rationale: Mutating or deleting review decisions erases audit trail. Corrections must be emitted as new events that downstream runtimes apply via reconciliation.
- Verification: Integration test — assert that correction application does not mutate or delete prior review records.

### Interaction Boundary Rules

**R08 — Matching Runtime Must Not Mutate Entity Runtime Stores**
- Rationale: Matching is a read-only consumer of the canonical index. Mutations must be owned by Entity Runtime.
- Verification: Integration test — assert that Matching Runtime interfaces to Entity Runtime are read-only (no create, update, delete operations).

**R09 — Monitoring Runtime Must Not Control Execution Flow**
- Rationale: Observability must be strictly read-only with respect to control flow. Monitoring must not start, stop, or modify workflow execution.
- Verification: Integration test — assert that Monitoring Runtime interfaces accept only telemetry data and return only metric/log responses.

**R10 — No Runtime May Bypass the Workflow Runtime for Cross-Runtime Orchestration**
- Rationale: Direct runtime-to-runtime orchestration outside of the event-driven data flow creates tight coupling and bypasses execution governance.
- Verification: Integration test — assert that all cross-runtime execution requests are routed through Workflow Runtime endpoints.

**R11 — Cross-Boundary Synchronous Calls Must Have a Registered ADR Exemption**
- Rationale: Synchronous cross-runtime calls defeat the async-first architecture. Any existing or new synchronous call must be documented via ADR with a justification and target remediation.
- Verification: CI lint check — assert that any synchronous cross-boundary import or call site has a corresponding exemption record.

### Shared Utility Rules

**R12 — Shared Utilities Must Not Import Runtime-Specific Modules**
- Rationale: Utility code in `src/utils.py`, `src/transform/` helpers, etc., must remain runtime-agnostic. Importing runtime-specific modules creates hidden coupling.
- Verification: Static import analysis — assert that `src/utils.py`, `src/config.py`, and shared helper modules do not import from runtime packages (`src/entity_runtime/`, `src/matching_runtime/`, etc.).

---

## Legacy Exemption Process

Some existing code paths may violate these boundary rules. Rather than blocking all progress, a formal exemption process allows documented, time-boxed exceptions.

### Exemption Criteria
An exemption may be granted when:
1. The violation is pre-existing (introduced before this boundary map was ratified).
2. Refactoring to comply would require disproportionate effort relative to the risk (e.g., a single synchronous call that is well-understood and monitored).
3. An architectural decision has been recorded to accept the coupling temporarily, with a target hardening phase for remediation.

### Exemption ADR Template

```markdown
# Status
Accepted (Exemption)

# Context
[Describe the boundary violation, the code paths involved, and why immediate compliance is not feasible.]

# Decision
A boundary exemption is granted for the following scope:
- **Runtime pair**: [Producer] → [Consumer]
- **Violation type**: [Import / Contract / Interaction]
- **Rule(s) breached**: [R01–R12]
- **Scope**: [Specific modules, functions, or call sites]

# Consequences
- This exemption must be reviewed quarterly.
- The violation must be remediated by [target milestone or date].
- The exemption record must be linked from affected code via a comment referencing this ADR.
```

### Exemption Lifecycle
1. **Creation**: ADR filed and approved. Exemption is registered in the boundary verification tooling as an allowed skip.
2. **Active**: Exemption is valid. Boundary verification CI steps will skip the exempted check.
3. **Quarterly Review**: Each exemption is reviewed on a quarterly cadence. The review outcome is recorded in the ADR.
4. **Expiration**: On the target milestone or date, the exemption expires. The boundary check becomes mandatory. CI will fail if the violation persists.

---

## Verification Strategy

Three tiers of verification, running from cheapest (static) to most expensive (integration):

### Tier 1 — Static Import Analysis
- **What**: Automated scan of Python import statements across runtime packages.
- **Tool**: Python script (`scripts/verify_boundaries.py`) or pytest-based static analysis.
- **Scope**: All runtime packages under `src/`.
- **Rules checked**: R01, R02, R03, R04, R05, R12.
- **Frequency**: Every PR and push to guarded branches.
- **Cost**: < 5 seconds.

### Tier 2 — Contract Adherence Smoke Tests
- **What**: For each runtime boundary, produce a test artifact and validate it against the Contract Registry schema.
- **Tool**: pytest test suite (`tests/boundaries/test_contract_adherence.py`).
- **Scope**: Each documented event flow (→) and request/response (↔).
- **Rules checked**: R06, R07.
- **Frequency**: Every PR and push to guarded branches.
- **Cost**: < 30 seconds (no external dependencies).

### Tier 3 — Cross-Boundary Interaction Integration Tests
- **What**: For each documented allowed and disallowed interaction, exercise the boundary and assert correct behaviour.
- **Tool**: pytest integration suite (`tests/boundaries/test_interactions.py`).
- **Scope**: All allowed (→, ↔, ↛, ←) and disallowed (✗) interactions.
- **Rules checked**: R08, R09, R10, R11.
- **Frequency**: PRs with runtime changes; nightly in CI.
- **Cost**: 1–5 minutes (may require mock runtime instances).

---

## CI Integration Strategy

### Boundary Verification CI Stage
A new CI stage called `boundary-verification` shall be added to the existing `.github/workflows/contract-validation.yml` workflow (or as a separate workflow).

| Step | Tier | Command | Gate |
|---|---|---|---|
| 1. Import isolation check | 1 | `python scripts/verify_boundaries.py` | Required |
| 2. Contract adherence tests | 2 | `python -m pytest tests/boundaries/test_contract_adherence.py -v` | Required |
| 3. Interaction boundary tests | 3 | `python -m pytest tests/boundaries/test_interactions.py -v` | Required on runtime changes |

### Gating Rules
- **PRs with no runtime changes**: Tiers 1 and 2 required. Tier 3 optional (skip if no runtime modules modified).
- **PRs with runtime changes**: All three tiers required.
- **Release branch pushes**: All three tiers required. Exemption bypasses are reviewed before release tagging.
- **Exemptions**: If a failing check has a registered ADR exemption ID, the check is skipped. The exemption ID must be passed as a pytest marker or script argument.

### Notification
- Boundary verification failures emit a clear error message identifying the rule violated, the runtime pair, and the specific module or call site.
- If the violation is not covered by an existing exemption, the error message includes a link to the exemption ADR template.

---

## Governance

### Ownership
- The boundary map is owned by the Platform Architect role.
- Changes to the dependency matrix or compliance rules require a new ADR and review by the runtime engineer.

### Review Cadence
- The boundary map is reviewed quarterly alongside the exemption register.
- Updates are triggered by: new runtime introduction, architecture review findings, or exemption expiration.

### Relationship to Other Documents
- Supersedes the informal boundary descriptions in `RUNTIME_BOUNDARIES.md` (Section "Allowed dependency directions" and "Forbidden coupling").
- Registered exemptions must be listed in `docs/adr/` and linked here.
- The verification strategy in this document is implemented per `TEST_PLAN_BOUNDARY_VERIFICATION.md`.

---

## Appendix A — Code Module to Runtime Mapping

| Runtime | Package Path(s) |
|---|---|
| Document Runtime | `src/document_engine/`, `src/extract/` |
| Workflow Runtime | `src/workflow_runtime/`, `src/workflows.py`, `src/orchestrator.py` |
| Entity Runtime | `src/entity_runtime/` |
| Matching Runtime | `src/matching_runtime/`, `src/transform/comparison_engine.py` |
| Review Runtime | `src/review_runtime/` |
| API Runtime | `src/api/` |
| Monitoring Runtime | `src/telemetry/`, `src/audit.py` |
| Shared / Utility | `src/utils.py`, `src/config.py`, `src/schema_utils.py` |

Note: Some modules may span multiple runtimes conceptually. The mapping above is the canonical assignment for boundary verification purposes.

End of document.