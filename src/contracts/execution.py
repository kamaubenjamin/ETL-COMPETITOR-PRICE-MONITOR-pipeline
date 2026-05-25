"""Execution metadata contracts used by API, history, telemetry, and scheduler."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from src.core.execution.status import ExecutionStatus


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


@dataclass(slots=True)
class ExecutionMetadata:
    workflow_id: str
    run_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = ExecutionStatus.PENDING.value
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    records_processed: int = 0
    alerts_generated: int = 0
    reports_generated: int = 0
    connector_type: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["started_at"] = to_iso(self.started_at)
        payload["completed_at"] = to_iso(self.completed_at)
        return payload


@dataclass(slots=True)
class ExecutionError:
    message: str
    error_type: str = "ExecutionError"
    step: Optional[str] = None
    connector_type: Optional[str] = None
    retryable: bool = False
    trace: Optional[str] = None

    def to_payload(self) -> Dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}
