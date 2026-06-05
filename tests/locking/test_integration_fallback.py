"""Provider fallback behavior verification tests.

Verifies that:
- DB provider failure falls back to file provider
- File provider failure falls back to memory provider
- All providers fail raises LockProviderError
- Fallback performance is acceptable
"""

import sqlite3
import time
from pathlib import Path
from typing import Generator

import pytest

from src.workflow_runtime.locking.execution_guard import WorkflowExecutionGuard
from src.workflow_runtime.locking.lock_provider import LockProviderRegistry
from src.workflow_runtime.locking.providers import (
    MemoryLockProvider,
    FileLockProvider,
    DBLockProvider,
)


class TestDBToFileFallback:
    """Verify DB provider failure falls back to file provider."""

    @pytest.fixture
    def closed_db_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """A DB connection that immediately fails."""
        conn = sqlite3.connect(":memory:")
        conn.close()
        yield conn

    @pytest.fixture
    def db_provider_failing(
        self, closed_db_connection: sqlite3.Connection
    ) -> DBLockProvider:
        """DBLockProvider with a closed connection (will fail on acquire)."""
        return DBLockProvider(closed_db_connection)

    @pytest.fixture
    def file_provider(self, tmp_path: Path) -> FileLockProvider:
        lock_dir = tmp_path / ".locks"
        lock_dir.mkdir(exist_ok=True)
        return FileLockProvider(str(lock_dir))

    def test_db_fails_falls_to_file(
        self,
        db_provider_failing: DBLockProvider,
        file_provider: FileLockProvider,
        memory_lock_provider: MemoryLockProvider,
    ) -> None:
        """DB provider fails, registry falls back to file provider."""
        registry = LockProviderRegistry()
        registry.register(db_provider_failing, priority=0)
        registry.register(file_provider, priority=10)
        registry.register(memory_lock_provider, priority=20)

        # Use resolve(None) to trigger priority-ordered fallback
        resolved = registry.resolve(None)
        assert isinstance(resolved, FileLockProvider), (
            f"Expected FileLockProvider, got {type(resolved).__name__}"
        )

    def test_db_fails_execution_continues_with_file(
        self,
        db_provider_failing: DBLockProvider,
        file_provider: FileLockProvider,
    ) -> None:
        """Execution should proceed via file provider after DB failure."""
        registry = LockProviderRegistry()
        registry.register(db_provider_failing, priority=0)
        registry.register(file_provider, priority=10)
        registry.register(MemoryLockProvider(), priority=20)

        resolved = registry.resolve(None)
        guard = WorkflowExecutionGuard(
            lock_provider=resolved,
            lease_duration_s=300,
            refresh_interval_s=30,
            max_retries=0,
        )

        result, lock = guard.execute(
            workflow_id="wf_db_fail_fallback",
            holder_id="runner",
            fn=lambda: "file_fallback_ok",
        )
        assert result == "file_fallback_ok"
        assert lock is not None


class TestFileToMemoryFallback:
    """Verify file provider failure falls back to memory provider."""

    @pytest.fixture
    def file_provider_failing(
        self, tmp_path: Path
    ) -> FileLockProvider:
        """FileLockProvider in a path that will fail."""
        return FileLockProvider(str(tmp_path / ".nonexistent_deep" / ".locks"))

    def test_file_fails_falls_to_memory(
        self,
    ) -> None:
        """File provider fails, registry falls back to memory provider."""
        # Use a mock provider that always raises LockProviderError
        from src.workflow_runtime.locking.exceptions import LockProviderError
        from src.workflow_runtime.locking.lock_provider import LockProvider

        class FailingFileProvider(LockProvider):
            def __init__(self):
                super().__init__(name="file")

            def acquire(self, lock_id, holder_id, lease_duration_s):
                raise LockProviderError("file", message="Simulated file lock failure")

            def release(self, lock):
                return False

            def refresh(self, lock):
                return None

        memory_provider = MemoryLockProvider()
        registry = LockProviderRegistry()
        registry.register(FailingFileProvider(), priority=0)
        registry.register(memory_provider, priority=10)

        resolved = registry.resolve(None)
        assert isinstance(resolved, MemoryLockProvider), (
            f"Expected MemoryLockProvider, got {type(resolved).__name__}"
        )

    def test_file_fails_execution_continues_with_memory(
        self,
        file_provider_failing: FileLockProvider,
    ) -> None:
        """Execution should proceed via memory provider after file failure."""
        memory_provider = MemoryLockProvider()
        registry = LockProviderRegistry()
        registry.register(file_provider_failing, priority=0)
        registry.register(memory_provider, priority=10)

        resolved = registry.resolve(None)
        guard = WorkflowExecutionGuard(
            lock_provider=resolved,
            lease_duration_s=300,
            refresh_interval_s=30,
            max_retries=0,
        )

        result, lock = guard.execute(
            workflow_id="wf_file_fail_fallback",
            holder_id="runner",
            fn=lambda: "memory_fallback_ok",
        )
        assert result == "memory_fallback_ok"
        assert lock is not None


class TestAllProvidersFail:
    """Verify all providers failing raises LockProviderError."""

    def test_all_providers_fail_raises_error(self) -> None:
        """All providers in registry fail, should raise error."""
        from src.workflow_runtime.locking.exceptions import LockProviderError
        from src.workflow_runtime.locking.lock_provider import LockProvider

        class AlwaysFailingProvider(LockProvider):
            def __init__(self):
                super().__init__(name="failing")

            def acquire(self, lock_id, holder_id, lease_duration_s):
                raise RuntimeError("Always fails")

            def release(self, lock):
                return False

            def refresh(self, lock):
                return None

        registry = LockProviderRegistry()
        registry.register(AlwaysFailingProvider(), priority=0)

        with pytest.raises(LockProviderError):
            registry.resolve(None)


class TestFallbackPerformance:
    """Verify fallback performance is acceptable."""

    def test_db_provider_latency(self) -> None:
        """Measure DB lock provider latency."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE workflow_locks (
                lock_id TEXT PRIMARY KEY,
                holder_id TEXT NOT NULL,
                acquired_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                expires_at TIMESTAMP NOT NULL,
                lease_duration_s INTEGER NOT NULL DEFAULT 300,
                hostname TEXT NOT NULL DEFAULT '',
                pid INTEGER,
                refresh_count INTEGER NOT NULL DEFAULT 0,
                last_refreshed_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
            );
        """)
        provider = DBLockProvider(conn)

        durations = []
        for _ in range(10):
            start = time.perf_counter()
            lock = provider.acquire(
                lock_id=f"wf_latency_{_}",
                holder_id="latency-test",
                lease_duration_s=300,
            )
            elapsed = time.perf_counter() - start
            durations.append(elapsed * 1000)  # Convert to ms
            if lock:
                provider.release(lock)

        avg_ms = sum(durations) / len(durations)
        # DB latency should be reasonable (< 50ms typical for in-memory)
        assert avg_ms < 50, f"Average DB latency too high: {avg_ms:.2f}ms"
        conn.close()

    def test_provider_fallback_execution(self) -> None:
        """Measure end-to-end time with fallback chain."""
        # Setup failing DB -> working file
        closed_conn = sqlite3.connect(":memory:")
        closed_conn.close()
        db_provider = DBLockProvider(closed_conn)

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            file_provider = FileLockProvider(str(Path(tmpdir) / ".locks"))

            registry = LockProviderRegistry()
            registry.register(db_provider, priority=0)
            registry.register(file_provider, priority=10)

            start = time.perf_counter()
            resolved = registry.resolve(None)
            resolve_time = time.perf_counter() - start

            assert isinstance(resolved, FileLockProvider)
            assert resolve_time < 0.5, (
                f"Fallback resolution too slow: {resolve_time*1000:.1f}ms"
            )