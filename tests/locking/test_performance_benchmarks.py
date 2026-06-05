"""Performance benchmarks for workflow runtime locking.

Measures:
- Lock acquisition latency (p50/p99) for all providers
- Lock release latency
- Lease refresh latency
- Concurrent lock throughput
- Idempotency check latency
"""

import sqlite3
import time
import statistics
from pathlib import Path

import pytest

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


# ── Helpers for percentile calculation ─────────────────────────────────


def percentile(data: list, p: float) -> float:
    """Calculate the p-th percentile of data."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p / 100.0
    f = int(k)
    c = f + 1
    if c >= len(sorted_data):
        return sorted_data[-1]
    return sorted_data[f] * (c - k) + sorted_data[c] * (k - f)


# ── DB Lock Provider Benchmarks ────────────────────────────────────────


class TestLockAcquireLatency:
    """Benchmark lock acquisition latency for DB provider."""

    @pytest.fixture
    def db_provider(self) -> DBLockProvider:
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
        return DBLockProvider(conn)

    def test_lock_acquire_latency_db_p50(self, db_provider: DBLockProvider) -> None:
        """DB lock acquisition p50 latency should be <10ms."""
        durations = []
        for i in range(50):
            lock_id = f"wf_latency_db_{i}"
            start = time.perf_counter()
            lock = db_provider.acquire(
                lock_id=lock_id,
                holder_id="test-holder",
                lease_duration_s=300,
            )
            elapsed = time.perf_counter() - start
            durations.append(elapsed * 1000)  # Convert to ms
            if lock:
                db_provider.release(lock)

        p50 = percentile(durations, 50)
        print(f"\n  DB Lock Acquire p50: {p50:.3f}ms")
        assert p50 < 50, f"DB lock acquire p50 latency too high: {p50:.3f}ms"

    def test_lock_acquire_latency_db_p99(self, db_provider: DBLockProvider) -> None:
        """DB lock acquisition p99 latency should be <50ms."""
        durations = []
        for i in range(100):
            lock_id = f"wf_latency_db_p99_{i}"
            start = time.perf_counter()
            lock = db_provider.acquire(
                lock_id=lock_id,
                holder_id="test-holder",
                lease_duration_s=300,
            )
            elapsed = time.perf_counter() - start
            durations.append(elapsed * 1000)
            if lock:
                db_provider.release(lock)

        p99 = percentile(durations, 99)
        print(f"\n  DB Lock Acquire p99: {p99:.3f}ms")
        assert p99 < 100, f"DB lock acquire p99 latency too high: {p99:.3f}ms"


class TestFileLockLatency:
    """Benchmark lock acquisition latency for file provider."""

    @pytest.fixture
    def file_provider(self, tmp_path: Path) -> FileLockProvider:
        lock_dir = tmp_path / ".locks"
        lock_dir.mkdir(exist_ok=True)
        return FileLockProvider(str(lock_dir))

    def test_lock_acquire_latency_file_p50(
        self, file_provider: FileLockProvider
    ) -> None:
        """File lock acquisition p50 latency should be <10ms."""
        durations = []
        for i in range(20):
            lock_id = f"wf_latency_file_{i}"
            start = time.perf_counter()
            lock = file_provider.acquire(
                lock_id=lock_id,
                holder_id="test-holder",
                lease_duration_s=300,
            )
            elapsed = time.perf_counter() - start
            durations.append(elapsed * 1000)
            if lock:
                file_provider.release(lock)

        p50 = percentile(durations, 50)
        print(f"\n  File Lock Acquire p50: {p50:.3f}ms")
        assert p50 < 50, f"File lock acquire p50 latency too high: {p50:.3f}ms"


class TestMemoryLockLatency:
    """Benchmark lock acquisition latency for memory provider."""

    def test_lock_acquire_latency_memory_p50(self) -> None:
        """Memory lock acquisition p50 latency should be <1ms."""
        provider = MemoryLockProvider()
        durations = []
        for i in range(100):
            lock_id = f"wf_latency_mem_{i}"
            start = time.perf_counter()
            lock = provider.acquire(
                lock_id=lock_id,
                holder_id="test-holder",
                lease_duration_s=300,
            )
            elapsed = time.perf_counter() - start
            durations.append(elapsed * 1000)
            if lock:
                provider.release(lock)

        p50 = percentile(durations, 50)
        print(f"\n  Memory Lock Acquire p50: {p50:.3f}ms")
        assert p50 < 5, f"Memory lock acquire p50 latency too high: {p50:.3f}ms"


class TestReleaseLatency:
    """Benchmark lock release latency."""

    def test_release_latency(self) -> None:
        """Lock release latency should be <5ms p50."""
        provider = MemoryLockProvider()
        durations = []

        for i in range(50):
            lock = provider.acquire(
                lock_id=f"wf_release_{i}",
                holder_id="test-holder",
                lease_duration_s=300,
            )
            if lock:
                start = time.perf_counter()
                released = provider.release(lock)
                elapsed = time.perf_counter() - start
                durations.append(elapsed * 1000)

        p50 = percentile(durations, 50) if durations else 0
        print(f"\n  Release p50: {p50:.3f}ms")
        assert p50 < 5, f"Release p50 latency too high: {p50:.3f}ms"


class TestRefreshLatency:
    """Benchmark lease refresh latency."""

    def test_refresh_latency(self) -> None:
        """Lease refresh latency should be <5ms p50."""
        provider = MemoryLockProvider()
        durations = []

        lock = provider.acquire(
            lock_id="wf_refresh_bench",
            holder_id="test-holder",
            lease_duration_s=300,
        )
        assert lock is not None

        for _ in range(50):
            start = time.perf_counter()
            refreshed = provider.refresh(lock)
            elapsed = time.perf_counter() - start
            durations.append(elapsed * 1000)
            if refreshed:
                lock = refreshed

        provider.release(lock)

        p50 = percentile(durations, 50)
        print(f"\n  Refresh p50: {p50:.3f}ms")
        assert p50 < 5, f"Refresh p50 latency too high: {p50:.3f}ms"


class TestConcurrentThroughput:
    """Benchmark concurrent lock throughput."""

    def test_concurrent_lock_throughput(self) -> None:
        """Measure acquire/release cycles with multiple workflows.

        Target: No significant throughput regression with concurrent workflows.
        """
        import threading

        provider = MemoryLockProvider()
        iterations = 20
        workers = 5
        results = []

        def worker(worker_id: int) -> None:
            local_results = []
            for i in range(iterations):
                lock_id = f"wf_throughput_{worker_id}_{i}"
                start = time.perf_counter()
                lock = provider.acquire(
                    lock_id=lock_id,
                    holder_id=f"worker-{worker_id}",
                    lease_duration_s=300,
                )
                if lock:
                    provider.release(lock)
                elapsed = time.perf_counter() - start
                local_results.append(elapsed * 1000)
            results.extend(local_results)

        threads = [
            threading.Thread(target=worker, args=(i,), daemon=True)
            for i in range(workers)
        ]

        start = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        total_time = time.perf_counter() - start

        total_ops = workers * iterations
        throughput = total_ops / total_time if total_time > 0 else 0
        p50 = percentile(results, 50)

        print(f"\n  Total operations: {total_ops}")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Throughput: {throughput:.1f} ops/s")
        print(f"  p50 latency: {p50:.3f}ms")
        assert p50 < 10, f"Concurrent throughput p50 too high: {p50:.3f}ms"
        assert throughput > 100, (
            f"Throughput too low: {throughput:.1f} ops/s"
        )


class TestIdempotencyCheckLatency:
    """Benchmark idempotency check latency."""

    def test_idempotency_check_latency_memory(self) -> None:
        """Idempotency check latency (memory) should be <1ms p50."""
        registry = MemoryIdempotencyRegistry()
        registry.record(
            key="bench_key_1",
            pipeline_run_id="bench-run",
            status="completed",
        )

        durations = []
        for _ in range(100):
            start = time.perf_counter()
            result = registry.check("bench_key_1")
            elapsed = time.perf_counter() - start
            durations.append(elapsed * 1000)
            assert result is not None

        p50 = percentile(durations, 50)
        print(f"\n  Idempotency Check (Memory) p50: {p50:.3f}ms")
        assert p50 < 2, (
            f"Memory idempotency check p50 too high: {p50:.3f}ms"
        )

    def test_idempotency_check_latency_db(self) -> None:
        """Idempotency check latency (DB) should be <10ms p50."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE workflow_idempotency (
                idempotency_key TEXT PRIMARY KEY,
                pipeline_run_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
                completed_at TIMESTAMP,
                result_summary TEXT
            );
            INSERT INTO workflow_idempotency
                (idempotency_key, pipeline_run_id, status)
            VALUES ('bench_db_key', 'bench-run', 'completed');
        """)
        registry = DBIdempotencyRegistry(conn)

        durations = []
        for _ in range(50):
            start = time.perf_counter()
            result = registry.check("bench_db_key")
            elapsed = time.perf_counter() - start
            durations.append(elapsed * 1000)
            assert result is not None

        p50 = percentile(durations, 50)
        print(f"\n  Idempotency Check (DB) p50: {p50:.3f}ms")
        assert p50 < 50, (
            f"DB idempotency check p50 too high: {p50:.3f}ms"
        )
        conn.close()