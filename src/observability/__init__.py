"""Neutral runtime observability contracts for the platform."""

from .contracts import (
    MetricType,
    RuntimeErrorRecord,
    RuntimeEvent,
    RuntimeMetric,
    RuntimeName,
    RuntimeSeverity,
    RuntimeStatus,
    RuntimeTraceContext,
)
from .emitter import EmitResult, ObservabilityEmitter, emit_event, emit_metric
from .sinks import (
    InMemoryObservabilitySink,
    JsonlObservabilitySink,
    NoOpObservabilitySink,
    ObservabilitySink,
)

__all__ = [
    "EmitResult",
    "InMemoryObservabilitySink",
    "JsonlObservabilitySink",
    "MetricType",
    "NoOpObservabilitySink",
    "ObservabilityEmitter",
    "ObservabilitySink",
    "RuntimeErrorRecord",
    "RuntimeEvent",
    "RuntimeMetric",
    "RuntimeName",
    "RuntimeSeverity",
    "RuntimeStatus",
    "RuntimeTraceContext",
    "emit_event",
    "emit_metric",
]
