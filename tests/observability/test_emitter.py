from src.observability.contracts import RuntimeEvent, RuntimeMetric, RuntimeTraceContext
from src.observability.emitter import ObservabilityEmitter, emit_event, emit_metric
from src.observability.sinks import InMemoryObservabilitySink


class FailingSink:
    def emit_event(self, event):
        raise RuntimeError("event sink failed")

    def emit_metric(self, metric):
        raise RuntimeError("metric sink failed")


def make_trace() -> RuntimeTraceContext:
    return RuntimeTraceContext.new_root(
        correlation_id="corr-1",
        trace_id="trace-1",
        span_id="span-1",
    )


def make_event() -> RuntimeEvent:
    return RuntimeEvent(
        event_type="workflow.run.started",
        runtime="workflow",
        operation="workflow.run",
        status="started",
        severity="info",
        trace=make_trace(),
    )


def make_metric() -> RuntimeMetric:
    return RuntimeMetric(
        metric_name="workflow.run.count",
        metric_type="counter",
        value=1,
        unit="count",
        runtime="workflow",
        dimensions={"runtime": "workflow"},
        trace=make_trace(),
    )


def test_emitter_forwards_records_to_sink():
    sink = InMemoryObservabilitySink()
    emitter = ObservabilityEmitter(sink=sink)
    event = make_event()
    metric = make_metric()

    event_result = emitter.emit_event(event)
    metric_result = emitter.emit_metric(metric)

    assert event_result.ok is True
    assert metric_result.ok is True
    assert sink.events == [event]
    assert sink.metrics == [metric]


def test_emitter_skips_when_disabled():
    sink = InMemoryObservabilitySink()
    emitter = ObservabilityEmitter(sink=sink, enabled=False)

    event_result = emitter.emit_event(make_event())
    metric_result = emitter.emit_metric(make_metric())

    assert event_result.ok is True
    assert event_result.skipped is True
    assert metric_result.ok is True
    assert metric_result.skipped is True
    assert sink.events == []
    assert sink.metrics == []


def test_emitter_suppresses_sink_event_errors():
    emitter = ObservabilityEmitter(sink=FailingSink())

    result = emitter.emit_event(make_event())

    assert result.ok is False
    assert result.suppressed_error == "RuntimeError"
    assert emitter.suppressed_error_count == 1


def test_emitter_suppresses_sink_metric_errors():
    emitter = ObservabilityEmitter(sink=FailingSink())

    result = emitter.emit_metric(make_metric())

    assert result.ok is False
    assert result.suppressed_error == "RuntimeError"
    assert emitter.suppressed_error_count == 1


def test_default_emit_helpers_are_noop_and_fail_open():
    assert emit_event(make_event()).ok is True
    assert emit_metric(make_metric()).ok is True
