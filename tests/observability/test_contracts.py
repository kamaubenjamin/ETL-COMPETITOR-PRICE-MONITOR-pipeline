import json

import pytest

from src.observability.contracts import (
    MetricType,
    RuntimeErrorRecord,
    RuntimeEvent,
    RuntimeMetric,
    RuntimeName,
    RuntimeSeverity,
    RuntimeStatus,
    RuntimeTraceContext,
)
from src.observability.registry import (
    ALLOWED_METRIC_DIMENSIONS,
    EVENT_TYPES,
    METRIC_NAMES,
)


def test_trace_context_serializes_to_plain_dict():
    trace = RuntimeTraceContext(
        correlation_id="corr-1",
        trace_id="trace-1",
        span_id="span-1",
        workflow_id="workflow-1",
        workflow_run_id="run-1",
    )

    payload = trace.to_dict()

    assert payload["correlation_id"] == "corr-1"
    assert payload["trace_id"] == "trace-1"
    assert payload["span_id"] == "span-1"
    json.dumps(payload)


def test_child_span_preserves_correlation_and_parent():
    root = RuntimeTraceContext.new_root(
        correlation_id="corr-1",
        trace_id="trace-1",
        span_id="span-root",
        workflow_id="workflow-1",
        workflow_run_id="run-1",
    )

    child = root.child_span(span_id="span-child", stage_name="entity_extract")

    assert child.correlation_id == "corr-1"
    assert child.trace_id == "trace-1"
    assert child.parent_span_id == "span-root"
    assert child.workflow_id == "workflow-1"
    assert child.stage_name == "entity_extract"


def test_trace_context_requires_core_ids():
    with pytest.raises(ValueError, match="correlation_id"):
        RuntimeTraceContext(correlation_id="", trace_id="trace-1", span_id="span-1")


def test_error_record_sanitizes_message():
    error = RuntimeErrorRecord(
        error_code="E_TEST",
        error_type="RuntimeError",
        message="failed with token=abc123",
        retryable=True,
        root_cause="authorization=Bearer abc123",
    )

    payload = error.to_dict()

    assert "abc123" not in payload["message"]
    assert "[REDACTED]" in payload["message"]
    assert "abc123" not in payload["root_cause"]
    json.dumps(payload)


def test_runtime_event_validates_and_serializes():
    trace = RuntimeTraceContext.new_root(
        correlation_id="corr-1",
        trace_id="trace-1",
        span_id="span-1",
    )
    event = RuntimeEvent(
        event_id="event-1",
        event_type="workflow.run.started",
        runtime=RuntimeName.WORKFLOW,
        operation="workflow.run",
        status=RuntimeStatus.STARTED,
        severity=RuntimeSeverity.INFO,
        trace=trace,
        attributes={
            "stage_name": "extract",
            "supplier_name": "secret supplier",
            "unexpected": "dropped",
        },
    )

    payload = event.to_dict()

    assert payload["event_id"] == "event-1"
    assert payload["event_type"] == "workflow.run.started"
    assert payload["runtime"] == "workflow"
    assert payload["status"] == "started"
    assert payload["severity"] == "info"
    assert payload["attributes"] == {"stage_name": "extract"}
    json.dumps(payload)


def test_runtime_event_rejects_unknown_values():
    trace = RuntimeTraceContext.new_root(
        correlation_id="corr-1",
        trace_id="trace-1",
        span_id="span-1",
    )

    with pytest.raises(ValueError, match="unknown event_type"):
        RuntimeEvent(
            event_type="workflow.run.unknown",
            runtime="workflow",
            operation="workflow.run",
            status="started",
            severity="info",
            trace=trace,
        )

    with pytest.raises(ValueError, match="invalid runtime"):
        RuntimeEvent(
            event_type="workflow.run.started",
            runtime="erp",
            operation="workflow.run",
            status="started",
            severity="info",
            trace=trace,
        )


def test_runtime_metric_validates_dimensions_and_serializes():
    trace = RuntimeTraceContext.new_root(
        correlation_id="corr-1",
        trace_id="trace-1",
        span_id="span-1",
    )
    metric = RuntimeMetric(
        metric_name="workflow.run.count",
        metric_type=MetricType.COUNTER,
        value=1,
        unit="count",
        runtime=RuntimeName.WORKFLOW,
        dimensions={
            "runtime": "workflow",
            "status": "succeeded",
            "stage_name": "extract",
        },
        trace=trace,
    )

    payload = metric.to_dict()

    assert payload["metric_name"] == "workflow.run.count"
    assert payload["metric_type"] == "counter"
    assert payload["runtime"] == "workflow"
    assert payload["dimensions"]["status"] == "succeeded"
    assert payload["trace"]["correlation_id"] == "corr-1"
    json.dumps(payload)


def test_runtime_metric_rejects_unknown_metric_and_dimension():
    with pytest.raises(ValueError, match="unknown metric_name"):
        RuntimeMetric(
            metric_name="workflow.run.mystery",
            metric_type="counter",
            value=1,
            unit="count",
            runtime="workflow",
        )

    with pytest.raises(ValueError, match="disallowed metric dimensions"):
        RuntimeMetric(
            metric_name="workflow.run.count",
            metric_type="counter",
            value=1,
            unit="count",
            runtime="workflow",
            dimensions={"customer_name": "secret"},
        )


def test_registry_contains_required_phase_1_names():
    assert "workflow.run.started" in EVENT_TYPES
    assert "entity.cas.conflict" in EVENT_TYPES
    assert "matching.decision.created" in EVENT_TYPES
    assert "workflow.run.count" in METRIC_NAMES
    assert "entity.cas.conflict.count" in METRIC_NAMES
    assert "matching.low_confidence.count" in METRIC_NAMES
    assert {"runtime", "operation", "status"} <= ALLOWED_METRIC_DIMENSIONS
