"""Neutral observability contracts.

This module intentionally imports only Python standard library modules and
neutral observability helpers. It must not import runtime internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .privacy import sanitize_attributes, sanitize_dimensions, sanitize_error_message
from .registry import (
    MetricType,
    RuntimeName,
    RuntimeSeverity,
    RuntimeStatus,
    enum_value,
    validate_event_type,
    validate_metric_dimensions,
    validate_metric_name,
)


def utc_now_iso() -> str:
    """Return a UTC timestamp formatted for JSON records."""

    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class RuntimeTraceContext:
    """Correlation context shared by passive observability records."""

    correlation_id: str
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    workflow_id: str | None = None
    workflow_run_id: str | None = None
    stage_name: str | None = None
    stage_run_id: str | None = None
    entity_version_key: str | None = None
    entity_id: str | None = None
    contract_name: str | None = None
    contract_version: str | None = None

    @classmethod
    def new_root(
        cls,
        *,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        span_id: str | None = None,
        workflow_id: str | None = None,
        workflow_run_id: str | None = None,
    ) -> "RuntimeTraceContext":
        """Create a root trace context."""

        return cls(
            correlation_id=correlation_id or f"corr-{uuid4()}",
            trace_id=trace_id or f"trace-{uuid4()}",
            span_id=span_id or f"span-{uuid4()}",
            workflow_id=workflow_id,
            workflow_run_id=workflow_run_id,
        )

    def child_span(
        self,
        *,
        span_id: str | None = None,
        stage_name: str | None = None,
        stage_run_id: str | None = None,
        entity_version_key: str | None = None,
        entity_id: str | None = None,
        contract_name: str | None = None,
        contract_version: str | None = None,
    ) -> "RuntimeTraceContext":
        """Create a child trace context preserving correlation and trace IDs."""

        return RuntimeTraceContext(
            correlation_id=self.correlation_id,
            trace_id=self.trace_id,
            span_id=span_id or f"span-{uuid4()}",
            parent_span_id=self.span_id,
            workflow_id=self.workflow_id,
            workflow_run_id=self.workflow_run_id,
            stage_name=stage_name if stage_name is not None else self.stage_name,
            stage_run_id=stage_run_id if stage_run_id is not None else self.stage_run_id,
            entity_version_key=(
                entity_version_key
                if entity_version_key is not None
                else self.entity_version_key
            ),
            entity_id=entity_id if entity_id is not None else self.entity_id,
            contract_name=contract_name if contract_name is not None else self.contract_name,
            contract_version=(
                contract_version if contract_version is not None else self.contract_version
            ),
        )

    def __post_init__(self) -> None:
        for field_name in ("correlation_id", "trace_id", "span_id"):
            if not getattr(self, field_name):
                raise ValueError(f"{field_name} is required")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""

        return {
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "workflow_id": self.workflow_id,
            "workflow_run_id": self.workflow_run_id,
            "stage_name": self.stage_name,
            "stage_run_id": self.stage_run_id,
            "entity_version_key": self.entity_version_key,
            "entity_id": self.entity_id,
            "contract_name": self.contract_name,
            "contract_version": self.contract_version,
        }


@dataclass(frozen=True)
class RuntimeErrorRecord:
    """Sanitized runtime error classification."""

    error_code: str
    error_type: str
    message: str
    retryable: bool
    root_cause: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("error_code", "error_type", "message"):
            if not getattr(self, field_name):
                raise ValueError(f"{field_name} is required")
        object.__setattr__(self, "message", sanitize_error_message(self.message))
        if self.root_cause is not None:
            object.__setattr__(
                self, "root_cause", sanitize_error_message(self.root_cause)
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""

        return {
            "error_code": self.error_code,
            "error_type": self.error_type,
            "message": self.message,
            "retryable": self.retryable,
            "root_cause": self.root_cause,
        }


@dataclass(frozen=True)
class RuntimeEvent:
    """A structured runtime event."""

    event_type: str
    runtime: RuntimeName | str
    operation: str
    status: RuntimeStatus | str
    severity: RuntimeSeverity | str
    trace: RuntimeTraceContext
    event_id: str = field(default_factory=lambda: f"event-{uuid4()}")
    event_version: str = "1.0"
    timestamp: str = field(default_factory=utc_now_iso)
    duration_ms: int | float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    error: RuntimeErrorRecord | None = None

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id is required")
        if not self.operation:
            raise ValueError("operation is required")
        if not isinstance(self.trace, RuntimeTraceContext):
            raise TypeError("trace must be a RuntimeTraceContext")
        object.__setattr__(self, "event_type", validate_event_type(self.event_type))
        object.__setattr__(
            self, "runtime", enum_value(self.runtime, RuntimeName, "runtime")
        )
        object.__setattr__(
            self, "status", enum_value(self.status, RuntimeStatus, "status")
        )
        object.__setattr__(
            self,
            "severity",
            enum_value(self.severity, RuntimeSeverity, "severity"),
        )
        object.__setattr__(
            self, "attributes", sanitize_attributes(self.attributes)
        )
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError("duration_ms must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""

        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "timestamp": self.timestamp,
            "runtime": self.runtime,
            "operation": self.operation,
            "status": self.status,
            "severity": self.severity,
            "trace": self.trace.to_dict(),
            "duration_ms": self.duration_ms,
            "attributes": dict(self.attributes),
            "error": self.error.to_dict() if self.error else None,
        }


@dataclass(frozen=True)
class RuntimeMetric:
    """A structured runtime metric."""

    metric_name: str
    metric_type: MetricType | str
    value: int | float
    unit: str
    runtime: RuntimeName | str
    dimensions: dict[str, Any] = field(default_factory=dict)
    trace: RuntimeTraceContext | None = None
    timestamp: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        if not self.unit:
            raise ValueError("unit is required")
        if not isinstance(self.value, int | float):
            raise TypeError("value must be numeric")
        object.__setattr__(self, "metric_name", validate_metric_name(self.metric_name))
        object.__setattr__(
            self,
            "metric_type",
            enum_value(self.metric_type, MetricType, "metric_type"),
        )
        object.__setattr__(
            self, "runtime", enum_value(self.runtime, RuntimeName, "runtime")
        )
        validate_metric_dimensions(self.dimensions)
        object.__setattr__(
            self, "dimensions", sanitize_dimensions(self.dimensions)
        )
        if self.trace is not None and not isinstance(self.trace, RuntimeTraceContext):
            raise TypeError("trace must be a RuntimeTraceContext when provided")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""

        return {
            "metric_name": self.metric_name,
            "metric_type": self.metric_type,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp,
            "runtime": self.runtime,
            "dimensions": dict(self.dimensions),
            "trace": self.trace.to_dict() if self.trace else None,
        }
