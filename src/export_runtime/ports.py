"""Structural ports for future export adapter implementations."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .payloads import ExportPayload
from .results import ExportAdapterResult


@runtime_checkable
class ExportAdapterPort(Protocol):
    """Deliver one sanitized payload and return one sanitized result."""

    def export(self, payload: ExportPayload) -> ExportAdapterResult: ...

