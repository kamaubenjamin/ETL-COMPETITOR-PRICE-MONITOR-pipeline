"""Shared fixtures for the Workflow Runtime Locking test suite."""

import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator

import pytest

from src.workflow_runtime.locking.models import LockAcquisition, IdempotencyRecord
from src.workflow_runtime.locking.providers import (
    MemoryLockProvider,
    FileLockProvider,
    DBLockProvider,
)
from src.workflow_runtime.locking.idempotency import (
    MemoryIdempotencyRegistry,
    DBIdempotencyRegistry,
)
from src.workflow_runtime.locking.lock_provider import LockProviderRegistry
from src.workflow_runtime.locking.execution_guard import WorkflowExecutionGuard


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


# ── Memory Lock Provider Fixtures ─────────────────────────────────────


@pytest.fixture
def memory_lock_provider() -> MemoryLockProvider:
    """A fresh MemoryLockProvider instance."""
    return MemoryLockProvider()


# ── File Lock Provider Fixtures ───────────────────────────────────────


@pytest.fixture
def temp_lock_dir(tmp_path: Path) -> Path:
    """Temporary directory for file lock tests."""
    lock_dir = tmp_path / ".locks"
    lock_dir.mkdir(exist_ok=True)
    return lock_dir


@pytest.fixture
def file_lock_provider(temp_lock_dir: Path) -> FileLockProvider:
    """A fresh FileLockProvider instance."""
    return FileLockProvider(str(temp_lock_dir))


# ── DB Lock Provider Fixtures ─────────────────────────────────────────


@pytest.fixture
def db_connection() -> Generator[sqlite3.Connection, None, None]:
    """In-memory SQLite database with workflow_locks and workflow_idempotency tables."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE workflow_locks (
            lock_id            TEXT PRIMARY KEY,
            holder_id          TEXT NOT NULL,
            acquired_at        TIMESTAMP NOT NULL DEFAULT (datetime('now')),
            expires_at         TIMESTAMP NOT NULL,
            lease_duration_s   INTEGER NOT NULL DEFAULT 300,
            hostname           TEXT NOT NULL DEFAULT '',
            pid                INTEGER,
            refresh_count      INTEGER NOT NULL DEFAULT 0,
            last_refreshed_at  TIMESTAMP NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE workflow_idempotency (
            idempotency_key    TEXT PRIMARY KEY,
            pipeline_run_id    TEXT NOT NULL,
            status             TEXT NOT NULL CHECK (status IN ('completed', 'failed', 'in_progress')),
            created_at         TIMESTAMP NOT NULL DEFAULT (datetime('now')),
            completed_at       TIMESTAMP,
            result_summary     TEXT
        );
    """)
    yield conn
    conn.close()


@pytest.fixture
def db_lock_provider(db_connection: sqlite3.Connection) -> DBLockProvider:
    """A fresh DBLockProvider instance with an in-memory DB."""
    return DBLockProvider(db_connection)


@pytest.fixture
def db_idempotency_registry(db_connection: sqlite3.Connection) -> DBIdempotencyRegistry:
    """A fresh DBIdempotencyRegistry instance with an in-memory DB."""
    return DBIdempotencyRegistry(db_connection)


# ── Memory Idempotency Registry Fixtures ──────────────────────────────


@pytest.fixture
def memory_idempotency_registry() -> MemoryIdempotencyRegistry:
    """A fresh MemoryIdempotencyRegistry instance."""
    return MemoryIdempotencyRegistry()


# ── Execution Guard Fixtures ──────────────────────────────────────────


@pytest.fixture
def execution_guard(memory_lock_provider: MemoryLockProvider) -> WorkflowExecutionGuard:
    """A WorkflowExecutionGuard with MemoryLockProvider."""
    return WorkflowExecutionGuard(
        lock_provider=memory_lock_provider,
        lease_duration_s=300,
        refresh_interval_s=30,
        max_retries=0,
    )


@pytest.fixture
def execution_guard_with_idempotency(
    memory_lock_provider: MemoryLockProvider,
    memory_idempotency_registry: MemoryIdempotencyRegistry,
) -> WorkflowExecutionGuard:
    """A WorkflowExecutionGuard with MemoryLockProvider and MemoryIdempotencyRegistry."""
    return WorkflowExecutionGuard(
        lock_provider=memory_lock_provider,
        idempotency_registry=memory_idempotency_registry,
        lease_duration_s=300,
        refresh_interval_s=30,
    )


# ── LockProviderRegistry Fixtures ─────────────────────────────────────


@pytest.fixture
def registry_with_all_providers(
    db_lock_provider: DBLockProvider,
    file_lock_provider: FileLockProvider,
    memory_lock_provider: MemoryLockProvider,
) -> LockProviderRegistry:
    """A LockProviderRegistry with all three providers registered."""
    registry = LockProviderRegistry()
    registry.register(db_lock_provider, priority=0)
    registry.register(file_lock_provider, priority=10)
    registry.register(memory_lock_provider, priority=20)
    return registry