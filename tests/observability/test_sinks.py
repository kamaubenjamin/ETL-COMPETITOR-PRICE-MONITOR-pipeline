import json

from src.observability.contracts import RuntimeEvent, RuntimeMetric, RuntimeTraceContext
from src.observability.sinks import (
    InMemoryObservabilitySink,
    JsonlObservabilitySink,
    NoOpObservabilitySink,
)


def make_trace() -> RuntimeTraceContext:
    return RuntimeTraceContext.new_root(
        correlation_id="corr-1",
        trace_id="trace-1",
        span_id="span-1",
    )


def make_event() -> RuntimeEvent:
    return RuntimeEvent(
        event_id="event-1",
        event_type="workflow.run.started",
        runtime="workflow",
        operation="workflow.run",
        status="started",
        severity="info",
        trace=make_trace(),
        attributes={"stage_name": "extract"},
    )


def make_metric() -> RuntimeMetric:
    return RuntimeMetric(
        metric_name="workflow.run.count",
        metric_type="counter",
        value=1,
        unit="count",
        runtime="workflow",
        dimensions={"runtime": "workflow", "status": "started"},
        trace=make_trace(),
    )


def test_noop_sink_accepts_records_without_side_effects():
    sink = NoOpObservabilitySink()

    sink.emit_event(make_event())
    sink.emit_metric(make_metric())


def test_in_memory_sink_captures_and_clears_records():
    sink = InMemoryObservabilitySink()
    event = make_event()
    metric = make_metric()

    sink.emit_event(event)
    sink.emit_metric(metric)

    assert sink.events == [event]
    assert sink.metrics == [metric]
    assert sink.events_by_type("workflow.run.started") == [event]
    assert sink.metrics_by_name("workflow.run.count") == [metric]

    sink.clear()

    assert sink.events == []
    assert sink.metrics == []


def test_jsonl_sink_writes_sanitized_json_records(tmp_path):
    path = tmp_path / "observability" / "records.jsonl"
    sink = JsonlObservabilitySink(path)

    sink.emit_event(make_event())
    sink.emit_metric(make_metric())

    lines = path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 2
    event_payload = json.loads(lines[0])
    metric_payload = json.loads(lines[1])
    assert event_payload["record_type"] == "event"
    assert event_payload["record"]["event_type"] == "workflow.run.started"
    assert metric_payload["record_type"] == "metric"
    assert metric_payload["record"]["metric_name"] == "workflow.run.count"
