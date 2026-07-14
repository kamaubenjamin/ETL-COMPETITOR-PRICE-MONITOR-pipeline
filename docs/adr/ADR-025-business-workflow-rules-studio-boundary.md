# ADR-025: Business Workflow / Rules Studio Boundary

## Status

Proposed for v0.20. Planning only; no implementation, endpoint, permission, migration, dependency, or UI behavior is authorized by this ADR alone.

## Context

The platform already has a deterministic Workflow Runtime with DSL parsing/validation, dependency resolution, DAG construction, operation registration, execution, locking, and read projections. Business users need a governed way to define and understand workflows without editing runtime configuration directly or gaining arbitrary execution capability.

Historical Sanifu/Docsift-style definitions contain useful business concepts and a broad operation vocabulary, but they cannot be executed safely or assumed equivalent to current runtime semantics. The platform also needs immutable published versions, drafts, approval, safe tests, tenant isolation, and audit lineage—concerns that do not belong inside the runtime executor.

## Decision

Create a separate `src/workflow_studio/` governance and policy package above the existing Workflow Runtime.

```text
FlowSync Rules Studio
  -> Authenticated Workflow Management API
  -> Workflow Definition Service
  -> Workflow DSL validation
  -> Operation / function allowlist
  -> Versioned workflow repository
  -> Dry-run / test execution boundary
  -> Existing Workflow Runtime
  -> Safe execution preview, audit, and publication state
```

Workflow Runtime remains execution authority. Workflow Studio owns definition contracts, operation descriptors, validation orchestration, drafts, immutable versions, approval/publication policy, legacy translation reports, preview policy, and safe audit intents. An outer adapter compiles a validated immutable Studio version to existing runtime contracts; the Studio does not implement a second scheduler or operation executor.

## Package Decision

Select `src/workflow_studio/` rather than `src/workflow_runtime/management/`.

The separate package makes the trust boundary explicit and avoids coupling runtime execution to API/UI governance, authoring state, approval, publication, and persistence decisions. Core Studio modules should import only the standard library and package-local modules. Narrow ports/adapters outside core integrate operation availability, Workflow Runtime preview, persistence, security, audit, fixtures, and API composition.

Placing authoring directly in Workflow Runtime is rejected because it would mix mutable drafts and business-facing validation with deterministic execution authority. Replacing the current runtime is also rejected.

## Definition Decision

Use immutable versioned workflow definitions containing ordered rules, explicit dependencies, conditions, allowlisted actions, input/output hints, safe metadata, trusted attribution, and publication metadata. Keep stable workflow identity separate from version identity.

Only drafts are editable. Published versions are immutable. Editing published behavior creates a derived draft. Deactivation changes activation state without rewriting content. Rollback publishes a new version derived from prior immutable content.

## Operation Catalog Decision

Maintain a Studio action catalog distinct from, but mapped to, the existing runtime operation registry. A catalog entry is publishable only when its runtime mapping, version, argument schema, contracts, determinism, resource limits, privacy policy, and tests are proven.

Known historical operation names may appear as unavailable migration references; recognition does not authorize execution. The catalog must explicitly reject arbitrary Python, eval/exec, shell, imports, raw SQL, unrestricted HTTP, filesystem, direct database writes, arbitrary JavaScript, secrets, unbounded recursion, direct ERP, export activation, and tenant-crossing lookup.

## Validation Decision

Apply ordered schema, semantic, dependency/DAG, runtime compatibility, security, and publication validation. Every issue uses a fixed code and safe bounded location/summary. Client validation is advisory only; API/service validation is authoritative.

The dependency validator rejects missing rules and cycles and derives stable topological order. Action and condition validators use fixed catalogs, restricted paths, bounded arguments, and protected-field policy. Runtime validation confirms an actual registered compatible operation and adapter before publication.

## Preview Decision

Provide a bounded dry-run port over approved fixtures or bounded privacy-checked inline samples. Preview uses the existing runtime through an isolated adapter and produces safe rule/stage summaries and redacted outputs.

Preview may not mutate Document State/lifecycle, export, ERP, production master data, schedules, alerts/email, external services, or workflow publication. It enforces sample, collection, rule/action/step, depth, duration, trace, and output limits. Raw exceptions, protected fields, secrets, paths, and unrestricted traces are excluded.

## Repository Decision

Define persistence-neutral repositories and use an in-memory implementation first. Evaluate SQLite later only after explicit schema/migration and transaction review. Do not store workflow definitions in Document State: document processing facts and workflow definition governance have different aggregate, versioning, approval, retention, and publication semantics.

## Legacy Compatibility Decision

Treat historical templates as source references and migration fixtures. A future strict importer produces a translation proposal and per-operation report: supported, partially supported, unsupported, or manual review. It retains bounded lineage, never executes source definitions, and never silently changes ordering, paths, defaults, or semantics. Imported results begin as drafts and pass all normal validation/test/approval/publication gates.

## API Decision

Plan authenticated tenant-scoped management endpoints for definitions, versions, validation, test preview, operation catalog, publication, deactivation, archival, and audit. The API owns identity, permissions, tenant scope, expected version, operation catalog, fixture eligibility, validation, approval, publication, concealment, and errors.

No endpoint is created by this ADR. Mutation design must include bounded payloads, optimistic concurrency, idempotency where applicable, audit intents, and published-version mutation denial.

## Security Decision

Evaluate dedicated workflow management permissions. Existing `workflow:read` may remain appropriate for reads; `workflow:run` does not imply create, edit, test, approve, publish, deactivate, or admin authority.

Tenant isolation precedes lookup. Cross-tenant platform administration is explicit and audited. Publication requires stronger authority than editing and may require author/reviewer separation. Definitions, samples, previews, and audit exclude credentials, tokens, claims, secrets, raw SQL, internal paths, executable source, unrestricted metadata, raw exceptions, and protected values.

## FlowSync Decision

Preserve the approved visual identity and API-authoritative request states. Start with structured forms and ordered rule cards, not a mandatory drag-and-drop programming canvas. FlowSync consumes the operation catalog and safe validation/preview/publication projections; it does not execute workflows, generate code, decide permissions, publish locally, mutate runtime registries, or call ERP/export/external services.

## LLM Decision

LLM execution is outside v0.20 v1 scope. Future LLM output is an untrusted suggestion only and must pass schema validation, semantic validation, deterministic dry run, human review, and authorized publication. An LLM cannot approve, publish, execute functions, decide permissions, or silently translate legacy rules.

## Consequences

### Positive

- Runtime execution authority remains deterministic and isolated.
- Business authoring gains explicit validation, version, approval, and audit ownership.
- Published history is immutable and rollback preserves lineage.
- Operation capability is visible without exposing arbitrary execution.
- Legacy migration becomes reviewable and non-silent.
- Safe preview can be tested before production publication/execution decisions.

### Negative

- A compiler/mapping layer is required between Studio actions and runtime operations.
- Definition persistence and publication need a new aggregate and transaction model.
- Preview fidelity depends on controlled adapter and fixture equivalence.
- Structured editing and validation require substantial contracts and UI states.
- Some historical rules will remain unsupported or require manual redesign.

## Alternatives Rejected

- **Edit runtime DSL directly in FlowSync:** exposes low-level execution configuration and weakens validation/governance.
- **Put Studio management inside Workflow Runtime:** mixes drafts/publication with execution authority and broadens the runtime boundary.
- **Execute raw legacy templates:** unsafe and semantically ambiguous.
- **Allow arbitrary scripting/functions:** violates deterministic, security, privacy, and operations constraints.
- **Store definitions in Document State:** wrong aggregate ownership and lifecycle.
- **Start with a drag-and-drop canvas:** adds complexity before contract, accessibility, and dependency semantics are proven.
- **Use an LLM as rule authority:** non-deterministic and bypasses review/publication governance.

## Deferred Decisions

Durable backend/schema, environment promotion, production execution binding, scheduler/events, live master-data adapters, queue/workers, retry/recovery, collaborative editing, visual canvas, reusable subworkflows, semantic/LLM suggestions, plugins/marketplace, ERP/export integration, and production operations.

## Acceptance

ADR-025 is accepted when owners approve the separate Studio package, Workflow Runtime execution authority, explicit operation catalog, no-arbitrary-code policy, immutable publication/version model, safe preview restrictions, legacy migration reporting, tenant/permission model, structured FlowSync direction, seven-phase plan, and production activation gates.

