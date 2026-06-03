"""Shared fixtures for the Workflow Runtime Locking test suite."""

from datetime import datetime, timedelta
from typing import Generator

import pytest

from src.workflow_runtime.locking.models import LockAcquisition, IdempotencyRecord


# ── Sample Data Fixtures ──────────────────────────────────────────────


@pytest.fixture
def sample_lock_acquisition() -> LockAcquisition:
    """A sample valid LockAcquisition instance."""
    now = datetime.utcnow()
    return LockAcquisition(
        lock_id="test_workflow",
        holder_id="host-1234-abc-def",
        acquired_at=now.isoformat(),
        expires_at=(now + timedelta(seconds=300)).isoformat(),
        lease_duration_s=300,
    )


@pytest.fixture
def sample_expired_lock_acquisition() -> LockAcquisition:
    """A LockAcquisition with an expired lease."""
    now = datetime.utcnow()
    return LockAcquisition(
        lock_id="expired_workflow",
        holder_id="host-9999-old-run",
        acquired_at=(now - timedelta(seconds=600)).isoformat(),
        expires_at=(now - timedelta(seconds=300)).isoformat(),
        lease_duration_s=300,
    )


@pytest.fixture
def sample_idempotency_record() -> IdempotencyRecord:
    """A sample valid IdempotencyRecord."""
    return IdempotencyRecord(
        idempotency_key="test_workflow-scheduled-2026-06-03T08:00",
        pipeline_run_id="run-001-abc-def",
        status="completed",
        created_at=datetime.utcnow().isoformat(),
    )


@pytest.fixture
def sample_in_progress_idempotency_record() -> IdempotencyRecord:
    """An IdempotencyRecord with 'in_progress' status."""
    return IdempotencyRecord(
        idempotency_key="test_workflow-scheduled-2026-06-03T09:00",
        pipeline_run_id="run-002-ghi-jkl",
        status="in_progress",
        created_at=datetime.utcnow().isoformat(),
    )


@pytest.fixture
def sample_failed_idempotency_record() -> IdempotencyRecord:
    """An IdempotencyRecord with 'failed' status."""
    return IdempotencyRecord(
        idempotency_key="test_workflow-scheduled-2026-06-03T10:00",
        pipeline_run_id="run-003-mno-pqr",
        status="failed",
        created_at=datetime.utcnow().isoformat(),
    )