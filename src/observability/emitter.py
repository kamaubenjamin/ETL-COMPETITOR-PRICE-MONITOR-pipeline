"""Fail-open wrapper for passive observability emission."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import RuntimeEvent, RuntimeMetric
from .sinks import NoOpObservabilitySink, ObservabilitySink


@dataclass(frozen=True)
class EmitResult:
    """Result of an observability emit attempt."""

    ok: bool
    skipped: bool = False
    suppressed_error: str | None = None


class ObservabilityEmitter:
    """Runtime-facing fail-open wrapper around an observability sink."""

    def __init__(self, sink: ObservabilitySink | None = None, enabled: bool = True) -> None:
        self.sink = sink or NoOpObservabilitySink()
        self.enabled = enabled
        self.suppressed_error_count = 0

    def emit_event(self, event: RuntimeEvent) -> EmitResult:
        """Emit an event without allowing sink errors to escape."""

        if not self.enabled:
            return EmitResult(ok=True, skipped=True)
        try:
            self.sink.emit_event(event)
        except Exception as exc:  # pragma: no cover - exact sink failures vary
            self.suppressed_error_count += 1
            return EmitResult(ok=False, suppressed_error=exc.__class__.__name__)
        return EmitResult(ok=True)

    def emit_metric(self, metric: RuntimeMetric) -> EmitResult:
        """Emit a metric without allowing sink errors to escape."""

        if not self.enabled:
            return EmitResult(ok=True, skipped=True)
        try:
            self.sink.emit_metric(metric)
        except Exception as exc:  # pragma: no cover - exact sink failures vary
            self.suppressed_error_count += 1
            return EmitResult(ok=False, suppressed_error=exc.__class__.__name__)
        return EmitResult(ok=True)


DEFAULT_EMITTER = ObservabilityEmitter()


def emit_event(event: RuntimeEvent) -> EmitResult:
    """Emit an event through the default no-op emitter."""

    return DEFAULT_EMITTER.emit_event(event)


def emit_metric(metric: RuntimeMetric) -> EmitResult:
    """Emit a metric through the default no-op emitter."""

    return DEFAULT_EMITTER.emit_metric(metric)
