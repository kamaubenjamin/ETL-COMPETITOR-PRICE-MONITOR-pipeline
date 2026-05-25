"""Standard workflow and connector execution statuses."""

from __future__ import annotations

from enum import StrEnum


class ExecutionStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


TERMINAL_STATUSES = {
    ExecutionStatus.SUCCESS.value,
    ExecutionStatus.FAILED.value,
    ExecutionStatus.PARTIAL_SUCCESS.value,
    ExecutionStatus.CANCELLED.value,
    ExecutionStatus.TIMEOUT.value,
}

ACTIVE_STATUSES = {
    ExecutionStatus.PENDING.value,
    ExecutionStatus.QUEUED.value,
    ExecutionStatus.RUNNING.value,
}


def normalize_status(status: str | None) -> str:
    if not status:
        return ExecutionStatus.PENDING.value
    normalized = status.strip().lower().replace("-", "_")
    if normalized == "partial":
        return ExecutionStatus.PARTIAL_SUCCESS.value
    if normalized in {item.value for item in ExecutionStatus}:
        return normalized
    return status
