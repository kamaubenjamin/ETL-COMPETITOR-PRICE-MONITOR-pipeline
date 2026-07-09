# ADR-011: Observability Improvements

- Status: Accepted
- Date: 2026-07-09
- Related Milestone: v0.5 Observability Improvements

## Context

The platform now has hardened Workflow Runtime locking and Entity Runtime concurrency controls, but it does not yet have a shared observability contract for runtime events, metrics, trace context, and sanitized errors. Existing runtime behavior can be tested locally, but operators and future maintainers need a consistent way to correlate workflow runs, stage execution, entity writes, matching decisions, lock contention, idempotency outcomes, and failure categories.

The repository roadmap identifies Observability Improvements as the next v0.5 Runtime Hardening objective. The future Monitoring Runtime is recognized as a platform concept, but it is not yet implemented and must not become a synchronous dependency of existing runtimes.

## Decision

Implement Observability Improvements v1 as passive, vendor-neutral runtime observability.

The v1 decision is to:

- define neutral observability contracts for runtime trace context, errors, events, and metrics,
- define stable runtime names, statuses, severities, metric types, event names, metric names, and metric dimensions,
- define privacy allowlists and sanitization helpers,
- keep contracts independent from Workflow, Entity, Matching, Document, Review, API, and Monitoring Runtime internals,
- serialize observability records to JSON-compatible dictionaries,
- defer sink implementation to Phase 2,
- defer runtime instrumentation to later phases,
- avoid dashboards, external monitoring vendors, and synchronous Monitoring Runtime dependencies.

## Consequences

### Positive

- Establishes a common language for runtime observability before instrumentation begins.
- Preserves runtime boundaries by putting contracts in a neutral package.
- Supports future local sinks, tests, and asynchronous Monitoring Runtime consumption.
- Reduces sensitive data leakage risk through explicit allowlists and sanitization.
- Keeps v1 small enough to fit the v0.5 hardening scope.

### Negative

- Adds a new cross-cutting package that all future instrumentation must use consistently.
- Requires event and metric registries to be maintained as new runtime paths are instrumented.
- Does not immediately provide dashboards, alerting, or external monitoring integrations.

## Alternatives Considered

- Reuse existing telemetry modules directly: rejected because current telemetry is pipeline-oriented and does not define neutral runtime-wide contracts or trace context.
- Add OpenTelemetry immediately: rejected for v1 because it introduces external concepts before the platform has stable internal contracts.
- Build Monitoring Runtime first: rejected because existing runtimes need passive contracts and correlation rules before a monitoring consumer exists.
- Emit free-form logs only: rejected because free-form logs do not provide stable metric dimensions, privacy controls, or deterministic tests.

## Compliance

- Contracts live in `src/observability/`.
- Phase 1 introduces no runtime instrumentation.
- Phase 1 introduces no sink implementation.
- Phase 1 introduces no external vendor dependency.
- Phase 1 must pass `pytest tests/observability -q`.
- Boundary verification must remain clean.

## Follow-up

Phase 2 will add fail-open sink infrastructure. Later phases will add Workflow Runtime, Entity Runtime, and Matching Runtime instrumentation using these contracts.

End of document.
