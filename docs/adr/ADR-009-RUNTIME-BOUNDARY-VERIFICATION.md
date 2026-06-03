# Status
Accepted (Architecture Phase — Implementation Pending)

# Context
The v0.5 Runtime Hardening milestone has completed two foundation deliverables:

1. **Contract Registry v1** — A repository-owned JSON Schema Draft 07 registry for core runtime artifacts, with example fixtures and local validation tests.
2. **CI Contract Validation v1** — A lightweight GitHub Actions workflow that validates Contract Registry schemas on PRs and release branches.

The PLATFORM_ARCHITECTURE_REVIEW.md identified that runtime boundaries are insufficiently enforced: several services assume synchronous interactions, some components cross runtime boundaries without explicit contracts, and there is no automated verification that runtime isolation is maintained during development.

The V0_5_RUNTIME_HARDENING_PLAN.md recommends Runtime Boundary Verification as the next objective (Focus Area #3), with an estimated effort of 2 person-weeks and medium architecture impact.

The existing `RUNTIME_BOUNDARIES.md` documents purpose, responsibilities, inputs, outputs, dependencies, forbidden dependencies, and owned data for seven runtimes (Document, Workflow, Entity, Matching, Review, API, Monitoring). However, this document is informal — it lacks:
- A machine-readable dependency matrix with explicit allowed/disallowed symbols per runtime pair.
- Verifiable compliance rules with unique identifiers.
- A formal exemption process for pre-existing boundary violations.
- A verification strategy with tiered test coverage.
- CI integration specifications.

# Decision
Adopt a structured Runtime Boundary Verification approach encompassing three artifacts and a three-tier verification strategy.

## Artifacts

1. **`docs/architecture/RUNTIME_BOUNDARY_MAP.md`** — Formalises the runtime boundary map with:
   - A 7×7 Runtime Dependency Matrix (Producer × Consumer) with explicit interaction symbols.
   - 12 Boundary Compliance Rules (R01–R12) covering import isolation, contract adherence, and interaction boundaries.
   - 4 Interaction Protocols (event-driven data flow, synchronous request/response, read-only queries, observability reads).
   - A Legacy Exemption Process with ADR template and quarterly review lifecycle.
   - A 3-Tier Verification Strategy (static import analysis, contract adherence smoke tests, cross-boundary interaction integration tests).
   - CI Integration Strategy with gating rules per branch/event type.

2. **`docs/architecture/TEST_PLAN_BOUNDARY_VERIFICATION.md`** — Defines the test implementation plan with:
   - 16 Tier 1 import isolation test scenarios (TI-01 to TI-16).
   - 6 Tier 2 contract adherence smoke test scenarios (CA-01 to CA-06).
   - 10 Tier 3 cross-boundary interaction test scenarios (IB-01 to IB-10).
   - Exemption test skip mechanism via `exemptions.json`.
   - Mock dependency specifications per runtime under test.
   - CI workflow configuration and gating rules.

3. **`docs/adr/ADR-009-RUNTIME-BOUNDARY-VERIFICATION.md`** (this document) — Records the architecture decision and consequences.

## Verification Strategy (3-Tier)

### Tier 1 — Static Import Analysis
- **What**: AST-based scan of Python import statements across runtime packages.
- **Rules verified**: R01 (Document→Entity/Matching/Review isolation), R02 (Entity→Matching/Review isolation), R03 (Matching→Document isolation), R04 (Review→Document/Entity isolation), R05 (API→Workflow-only), R12 (shared utilities isolation).
- **Cost**: < 5 seconds.
- **Gate**: Required on all PRs and branch pushes.

### Tier 2 — Contract Adherence Smoke Tests
- **What**: For each runtime boundary, validate emitted artifacts against Contract Registry schemas.
- **Rules verified**: R06 (schema adherence), R07 (append-only corrections).
- **Cost**: < 30 seconds.
- **Gate**: Required on all PRs and branch pushes.

### Tier 3 — Cross-Boundary Interaction Integration Tests
- **What**: Exercise allowed and disallowed interactions between runtime pairs with mocked dependencies.
- **Rules verified**: R08 (read-only matching), R09 (observability isolation), R10 (orchestration via Workflow), R11 (exemptions required for synchronous calls).
- **Cost**: 1–5 minutes.
- **Gate**: Required on PRs with runtime changes and release branches.

## Exemption Process
Pre-existing boundary violations that cannot be immediately remediated are recorded via ADR exemption with:
- Rule(s) breached.
- Specific scope (modules, functions, call sites).
- Target remediation milestone.
- Quarterly review cadence.
- Expiration date.

Exemptions are registered in `tests/boundaries/exemptions.json` and automatically skipped during verification.

# Consequences

## Benefits
1. **Enforceable boundaries**: The 12 compliance rules provide a clear, verifiable standard for runtime isolation.
2. **CI gating**: Boundary violations are caught before merge, preventing silent regressions.
3. **Controlled exemptions**: Legacy violations are documented with expiry, preventing indefinite technical debt.
4. **Incremental adoption**: Tiers 1 and 2 are cheap (< 30 seconds combined) and can be enabled immediately. Tier 3 can be phased in as test infrastructure matures.
5. **Future-proofing**: Adding a new runtime requires a boundary map entry, import isolation tests, and contract adherence tests — the process is documented.

## Tradeoffs
1. **Test harness effort**: The Tier 3 interaction tests require mock infrastructure per runtime. Initial implementation may take longer than the 1–5 minute execution time suggests.
2. **False positives**: Static import analysis may flag imports that are only used in test code or type-checking blocks. The exemption process handles these, but initial tuning is expected.
3. **Exemption accretion**: Without disciplined quarterly reviews, exemptions may accumulate and erode boundary enforcement. The quarterly review cadence mitigates this but requires ongoing governance attention.

## Future Implications
1. **Schema compatibility checking**: This ADR does not implement compatibility diffing. A future hardening phase should add schema compatibility checks against the released baseline.
2. **ADR enforcement for breaking changes**: This ADR does not automate ADR creation for MAJOR schema version bumps. Governance is manual and relies on CI failure notices.
3. **Runtime boundary enforcement in production**: The current approach is limited to pre-merge verification. In-production boundary enforcement (e.g., runtime assertions or service mesh policies) is deferred to a later milestone.

# Exemption Template
When a boundary exemption is required (pre-existing violation requiring deferred remediation), use the following structure as a new ADR or as a sub-record under this ADR:

```markdown
# Status
Accepted (Exemption under ADR-009)

# Context
[Describe the boundary violation, the code paths involved, and why immediate compliance is not feasible.]

# Decision
A boundary exemption is granted for the following scope:
- **Runtime pair**: [Producer] → [Consumer]
- **Violation type**: [Import / Contract / Interaction]
- **Rule(s) breached**: [R01–R12]
- **Scope**: [Specific modules, functions, or call sites]
- **Justification**: [Why immediate compliance is disproportionate to the risk]

# Consequences
- This exemption must be reviewed quarterly.
- The violation must be remediated by [target milestone or date].
- The exemption record must be linked from affected code via a comment referencing this ADR.
- The exemption must be registered in `tests/boundaries/exemptions.json`.
```

End of document.