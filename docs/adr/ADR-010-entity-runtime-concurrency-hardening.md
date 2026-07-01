# ADR-010: Entity Runtime Concurrency Hardening

- Status: Accepted
- Date: 2026-07-01
- Related Milestone: v0.5 Entity Runtime Concurrency Hardening

## Context

The Entity Runtime previously produced immutable entity sets in memory without any persistence-level concurrency controls. In multi-worker or retry-heavy workflows, concurrent writes to the same logical entity could result in lost updates, duplicate writes, or inconsistent state. The runtime also lacked execution leases, idempotency protection, and a versioned persistence path for crash-safe writes.

## Decision

Implement a phased concurrency hardening strategy for the Entity Runtime that adds:

- a versioned entity store for append-only entity history,
- optimistic locking with compare-and-swap semantics,
- pessimistic lock escalation for hot entities,
- execution leases for crash recovery,
- idempotency tracking for duplicate write prevention,
- backward-compatible runtime integration that preserves the legacy in-memory path when concurrency is disabled.

## Consequences

### Positive

- Prevents lost updates and duplicate writes for entity operations.
- Enables deterministic recovery after lease expiry or interrupted writes.
- Preserves backward compatibility through an opt-in configuration path.
- Provides a clear basis for future review and ERP runtime integration.

### Negative

- Adds storage and operational complexity relative to the original in-memory runtime.
- Requires the version store to be initialized and available for the hardened path.
- Some operations now carry additional metadata such as entity versions and lease state.

## Implementation Notes

The implementation is delivered in phases:

1. Foundation: contracts, configuration, exceptions, and persistence abstractions.
2. Infrastructure: version store, idempotency registry, optimistic/pessimistic locking, lease management, and guard orchestration.
3. Runtime Integration: orchestrator and workflow adapter integration.
4. Verification: unit, integration, regression, and recovery tests.
5. Documentation & Release: milestone summary, handoff, ADR, and release notes.

## Alternatives Considered

- Purely in-memory merge semantics without persistence: rejected because it does not solve duplicate write or crash-recovery concerns.
- Event sourcing only: rejected for v1 due to scope and compatibility constraints.
- Full pessimistic locking for all entity operations: rejected because it adds unnecessary contention for low-risk operations.

## Follow-up

Future work may expand the model with richer reconciliation, archival policies, and observability around concurrency events.
