"""Registries for neutral observability names and dimensions."""

from __future__ import annotations

from enum import Enum
from typing import Final


class RuntimeName(str, Enum):
    """Known platform runtime names for observability records."""

    WORKFLOW = "workflow"
    ENTITY = "entity"
    MATCHING = "matching"
    DOCUMENT = "document"
    REVIEW = "review"
    API = "api"
    MONITORING = "monitoring"
    CONTRACT = "contract"


class RuntimeStatus(str, Enum):
    """Common lifecycle status values for runtime events."""

    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRIED = "retried"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


class RuntimeSeverity(str, Enum):
    """Severity values for runtime events."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(str, Enum):
    """Supported metric shapes."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


EVENT_TYPES: Final[frozenset[str]] = frozenset(
    {
        "workflow.run.started",
        "workflow.run.succeeded",
        "workflow.run.failed",
        "workflow.stage.started",
        "workflow.stage.succeeded",
        "workflow.stage.failed",
        "workflow.lock.acquire.started",
        "workflow.lock.acquire.succeeded",
        "workflow.lock.acquire.failed",
        "workflow.lease.renewed",
        "workflow.idempotency.duplicate_detected",
        "entity.write.started",
        "entity.write.succeeded",
        "entity.write.failed",
        "entity.cas.conflict",
        "entity.lock.escalated",
        "entity.lease.expired",
        "entity.idempotency.duplicate_detected",
        "matching.decision.created",
        "matching.low_confidence_detected",
        "matching.no_match_detected",
        "contract.validation.failed",
    }
)


METRIC_NAMES: Final[frozenset[str]] = frozenset(
    {
        "workflow.run.count",
        "workflow.run.duration_ms",
        "workflow.run.failure.count",
        "workflow.stage.duration_ms",
        "workflow.stage.failure.count",
        "workflow.lock.contention.count",
        "workflow.lock.acquire.duration_ms",
        "workflow.lease.recovery.count",
        "workflow.idempotency.duplicate.count",
        "entity.write.count",
        "entity.write.duration_ms",
        "entity.cas.conflict.count",
        "entity.lock.escalation.count",
        "entity.lease.expiry.count",
        "entity.idempotency.duplicate.count",
        "matching.decision.count",
        "matching.low_confidence.count",
        "contract.validation.failure.count",
    }
)


ALLOWED_METRIC_DIMENSIONS: Final[frozenset[str]] = frozenset(
    {
        "runtime",
        "operation",
        "status",
        "stage_name",
        "lock_provider",
        "entity_type",
        "match_strategy",
        "contract_name",
        "contract_version",
        "error_code",
    }
)


ALLOWED_EVENT_ATTRIBUTES: Final[frozenset[str]] = frozenset(
    {
        "runtime",
        "operation",
        "status",
        "stage_name",
        "stage_run_id",
        "lock_provider",
        "lease_status",
        "idempotency_status",
        "fallback_provider",
        "entity_type",
        "entity_version",
        "entity_version_key",
        "match_strategy",
        "candidate_count",
        "confidence_bucket",
        "contract_name",
        "contract_version",
        "error_code",
        "retryable",
        "duration_ms",
        "count",
    }
)


def enum_value(value: str | Enum, enum_type: type[Enum], field_name: str) -> str:
    """Return an enum value string, validating plain strings."""

    if isinstance(value, enum_type):
        enum_member = value
    else:
        try:
            enum_member = enum_type(value)
        except ValueError as exc:
            raise ValueError(f"invalid {field_name}: {value!r}") from exc
    return str(enum_member.value)


def validate_event_type(event_type: str) -> str:
    """Validate and return a registered event type."""

    if event_type not in EVENT_TYPES:
        raise ValueError(f"unknown event_type: {event_type!r}")
    return event_type


def validate_metric_name(metric_name: str) -> str:
    """Validate and return a registered metric name."""

    if metric_name not in METRIC_NAMES:
        raise ValueError(f"unknown metric_name: {metric_name!r}")
    return metric_name


def validate_metric_dimensions(dimensions: dict[str, object]) -> dict[str, object]:
    """Validate metric dimension keys against the low-cardinality allowlist."""

    invalid = sorted(set(dimensions) - ALLOWED_METRIC_DIMENSIONS)
    if invalid:
        raise ValueError(f"disallowed metric dimensions: {invalid}")
    return dict(dimensions)
