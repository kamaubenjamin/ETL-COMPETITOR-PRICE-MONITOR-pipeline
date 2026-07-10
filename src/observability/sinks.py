"""Local, vendor-neutral observability sinks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from .contracts import RuntimeEvent, RuntimeMetric


class ObservabilitySink(Protocol):
    """Protocol for passive observability sinks."""

    def emit_event(self, event: RuntimeEvent) -> None:
        """Emit a runtime event."""

    def emit_metric(self, metric: RuntimeMetric) -> None:
        """Emit a runtime metric."""


class NoOpObservabilitySink:
    """Default sink that drops all observability records."""

    def emit_event(self, event: RuntimeEvent) -> None:
        """Drop a runtime event."""

    def emit_metric(self, metric: RuntimeMetric) -> None:
        """Drop a runtime metric."""


class InMemoryObservabilitySink:
    """Test sink that stores emitted records in memory."""

    def __init__(self) -> None:
        self.events: list[RuntimeEvent] = []
        self.metrics: list[RuntimeMetric] = []

    def emit_event(self, event: RuntimeEvent) -> None:
        """Store a runtime event."""

        self.events.append(event)

    def emit_metric(self, metric: RuntimeMetric) -> None:
        """Store a runtime metric."""

        self.metrics.append(metric)

    def clear(self) -> None:
        """Clear captured records."""

        self.events.clear()
        self.metrics.clear()

    def events_by_type(self, event_type: str) -> list[RuntimeEvent]:
        """Return captured events matching an event type."""

        return [event for event in self.events if event.event_type == event_type]

    def metrics_by_name(self, metric_name: str) -> list[RuntimeMetric]:
        """Return captured metrics matching a metric name."""

        return [metric for metric in self.metrics if metric.metric_name == metric_name]


class JsonlObservabilitySink:
    """Local JSONL sink for development and tests.

    This sink performs only local filesystem writes and does not create network
    or external vendor dependencies.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def emit_event(self, event: RuntimeEvent) -> None:
        """Append an event record to the JSONL file."""

        self._append({"record_type": "event", "record": event.to_dict()})

    def emit_metric(self, metric: RuntimeMetric) -> None:
        """Append a metric record to the JSONL file."""

        self._append({"record_type": "metric", "record": metric.to_dict()})

    def _append(self, payload: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
