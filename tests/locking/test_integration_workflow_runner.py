"""Integration tests for WorkflowRunner with WorkflowExecutionGuard integration.

Tests the Phase 3 integration where WorkflowExecutionGuard is wired into
WorkflowRunner.run() to provide lock lifecycle management and idempotency
deduplication.
"""

from typing import Any, Dict

import pytest

from src.core.execution.status import ExecutionStatus
from src.workflow_runtime.contracts.workflow_definition import (
    WorkflowDefinition,
    StageDefinition,
)
from src.workflow_runtime.runtime.workflow_runner import (
    WorkflowRunner,
    generate_idempotency_key,
)
from src.workflow_runtime.locking.execution_guard import WorkflowExecutionGuard
from src.workflow_runtime.locking.providers import MemoryLockProvider
from src.workflow_runtime.locking.idempotency import MemoryIdempotencyRegistry


# ── Helper Fixtures ────────────────────────────────────────────────────


@pytest.fixture
def sample_definition() -> WorkflowDefinition:
    """A minimal, valid workflow definition for testing."""
    return WorkflowDefinition(
        workflow_id="test_wf_integration",
        name="Integration Test Workflow",
        workspace_id="test_workspace",
        stages=[
            StageDefinition(
                name="pass_through",
                type="transform",
                config={"operation": "identity"},
            ),
        ],
        version="1.0.0",
        enabled=True,
    )


@pytest.fixture
def sample_definition_b() -> WorkflowDefinition:
    """A different workflow definition for testing cross-workflow concurrency."""
    return WorkflowDefinition(
        workflow_id="test_wf_integration_b",
        name="Integration Test Workflow B",
        workspace_id="test_workspace",
        stages=[
            StageDefinition(
                name="pass_through",
                type="transform",
                config={"operation": "identity"},
            ),
        ],
        version="1.0.0",
        enabled=True,
    )


@pytest.fixture
def memory_idempotency_registry() -> MemoryIdempotencyRegistry:
    return MemoryIdempotencyRegistry()


@pytest.fixture
def memory_guard(memory_idempotency_registry: MemoryIdempotencyRegistry) -> WorkflowExecutionGuard:
    """A WorkflowExecutionGuard with MemoryLockProvider and idempotency registry."""
    return WorkflowExecutionGuard(
        lock_provider=MemoryLockProvider(),
        idempotency_registry=memory_idempotency_registry,
        lease_duration_s=300,
        refresh_interval_s=30,
        max_retries=0,
    )


@pytest.fixture
def guarded_runner(
    memory_guard: WorkflowExecutionGuard,
    memory_idempotency_registry: MemoryIdempotencyRegistry,
) -> WorkflowRunner:
    """A WorkflowRunner with guard and idempotency registry configured."""
    return WorkflowRunner(
        execution_guard=memory_guard,
        idempotency_registry=memory_idempotency_registry,
    )


@pytest.fixture
def unguarded_runner() -> WorkflowRunner:
    """A WorkflowRunner without guard (original behaviour)."""
    return WorkflowRunner()


# ── Tests: generate_idempotency_key ────────────────────────────────────


class TestGenerateIdempotencyKey:
    def test_scheduled_key_is_deterministic(self) -> None:
        k1 = generate_idempotency_key("wf1", "2026-06-03T08:00:00")
        k2 = generate_idempotency_key("wf1", "2026-06-03T08:00:00")
        assert k1 == k2
        assert "scheduled" in k1

    def test_different_slots_produce_different_keys(self) -> None:
        k1 = generate_idempotency_key("wf1", "2026-06-03T08:00:00")
        k2 = generate_idempotency_key("wf1", "2026-06-03T09:00:00")
        assert k1 != k2

    def test_manual_key_includes_uuid(self) -> None:
        k1 = generate_idempotency_key("wf1", scope="manual")
        k2 = generate_idempotency_key("wf1", scope="manual")
        assert k1 != k2  # UUID makes them unique

    def test_custom_scope(self) -> None:
        k = generate_idempotency_key("wf1", "2026-06-03T08:00:00", scope="api")
        assert "api" in k


# ── Tests: Unguarded Runner (Backward Compatibility) ───────────────────


class TestUnguardedRunner:
    """Verify the unguarded runner preserves original behaviour."""

    def test_run_success(self, unguarded_runner: WorkflowRunner,
                         sample_definition: WorkflowDefinition) -> None:
        result = unguarded_runner.run(sample_definition, initial_artifact={"data": 1})
        assert result.workflow_id == "test_wf_integration"
        assert result.overall_status == ExecutionStatus.SUCCESS.value
        assert result.lock_status == "not_locked"  # Unguarded runner always reports not_locked
        assert result.idempotency_key is None  # Not provided

    def test_run_with_metadata(self, unguarded_runner: WorkflowRunner,
                               sample_definition: WorkflowDefinition) -> None:
        result = unguarded_runner.run(
            sample_definition,
            initial_artifact={"data": 1},
            metadata={"trigger": "manual"},
        )
        assert result.overall_status == ExecutionStatus.SUCCESS.value

    def test_run_idempotency_key_passthrough_no_guard(
        self, unguarded_runner: WorkflowRunner,
        sample_definition: WorkflowDefinition,
    ) -> None:
        """When no guard is configured, idempotency_key is passed through as metadata."""
        result = unguarded_runner.run(
            sample_definition,
            initial_artifact={"data": 1},
            idempotency_key="test-key-123",
        )
        # Without guard, key is stored in result as provided
        assert result.idempotency_key == "test-key-123"
        assert result.lock_status == "not_locked"


# ── Tests: Guarded Runner ──────────────────────────────────────────────


class TestGuardedRunner:
    """Verify the guarded runner provides lock lifecycle management."""

    def test_run_success_with_guard(
        self,
        guarded_runner: WorkflowRunner,
        sample_definition: WorkflowDefinition,
    ) -> None:
        result = guarded_runner.run(sample_definition, initial_artifact={"data": 1})
        assert result.workflow_id == "test_wf_integration"
        assert result.overall_status == ExecutionStatus.SUCCESS.value
        assert result.lock_status == "acquired"

    def test_run_success_with_idempotency_key(
        self,
        guarded_runner: WorkflowRunner,
        sample_definition: WorkflowDefinition,
    ) -> None:
        key = generate_idempotency_key("test_wf_integration", "2026-06-03T08:00:00")
        result = guarded_runner.run(
            sample_definition,
            initial_artifact={"data": 1},
            idempotency_key=key,
        )
        assert result.overall_status == ExecutionStatus.SUCCESS.value
        assert result.lock_status == "acquired"
        assert result.idempotency_key == key

    def test_idempotency_skip_returns_cached(
        self,
        guarded_runner: WorkflowRunner,
        sample_definition: WorkflowDefinition,
    ) -> None:
        key = generate_idempotency_key("test_wf_integration", "2026-06-03T09:00:00")

        # First run completes normally
        result1 = guarded_runner.run(
            sample_definition,
            initial_artifact={"data": 1},
            idempotency_key=key,
        )
        assert result1.overall_status == ExecutionStatus.SUCCESS.value

        # Second run with same key — should skip
        result2 = guarded_runner.run(
            sample_definition,
            initial_artifact={"data": "should_not_run"},
            idempotency_key=key,
        )
        assert result2.overall_status == ExecutionStatus.SUCCESS.value
        assert result2.lock_status == "rejected_duplicate"

    def test_concurrent_same_workflow_rejected(
        self,
        sample_definition: WorkflowDefinition,
    ) -> None:
        """Two concurrent runs of the same workflow — second should be rejected."""
        provider = MemoryLockProvider()
        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            lease_duration_s=300,
            refresh_interval_s=30,
            max_retries=0,
        )
        runner = WorkflowRunner(execution_guard=guard)

        # Pre-acquire the lock via provider to simulate another run in progress
        import uuid
        provider.acquire(
            lock_id="test_wf_integration",
            holder_id=str(uuid.uuid4()),
            lease_duration_s=300,
        )

        # Runner should fail to acquire lock and return rejected_busy
        result2 = runner.run(
            sample_definition,
            initial_artifact={"data": "second"},
        )
        assert result2.lock_status == "rejected_busy"
        assert result2.overall_status == ExecutionStatus.FAILED.value
        assert "Lock acquisition failed" in (result2.error or "")

    def test_concurrent_different_workflows_allowed(
        self,
        sample_definition: WorkflowDefinition,
        sample_definition_b: WorkflowDefinition,
    ) -> None:
        """Different workflows can run concurrently."""
        guard = WorkflowExecutionGuard(
            lock_provider=MemoryLockProvider(),
            lease_duration_s=300,
            refresh_interval_s=30,
            max_retries=0,
        )
        runner_a = WorkflowRunner(execution_guard=guard)
        runner_b = WorkflowRunner(execution_guard=guard)

        r1 = runner_a.run(sample_definition, initial_artifact={"data": "a"})
        r2 = runner_b.run(sample_definition_b, initial_artifact={"data": "b"})
        assert r1.overall_status == ExecutionStatus.SUCCESS.value
        assert r1.lock_status == "acquired"
        assert r2.overall_status == ExecutionStatus.SUCCESS.value
        assert r2.lock_status == "acquired"

    def test_lock_status_not_locked_without_guard(
        self,
        unguarded_runner: WorkflowRunner,
        sample_definition: WorkflowDefinition,
    ) -> None:
        """Runner without guard should produce lock_status='not_locked'."""
        result = unguarded_runner.run(sample_definition)
        assert result.lock_status == "not_locked"


# ── Tests: Error Propagation ───────────────────────────────────────────


class TestErrorPropagation:
    def test_lock_error_returns_workflow_result(
        self,
        sample_definition: WorkflowDefinition,
    ) -> None:
        """Lock acquisition error should return WorkflowResult, not raise."""
        provider = MemoryLockProvider()
        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            lease_duration_s=300,
            refresh_interval_s=30,
            max_retries=0,
        )
        runner = WorkflowRunner(execution_guard=guard)

        # Acquire lock manually via provider to block the runner
        import uuid
        provider.acquire(
            lock_id="test_wf_integration",
            holder_id=str(uuid.uuid4()),
            lease_duration_s=300,
        )

        # Runner should get lock acquisition error returned as WorkflowResult
        result = runner.run(sample_definition, initial_artifact={"data": 1})
        assert result.lock_status == "rejected_busy"
        assert result.overall_status == ExecutionStatus.FAILED.value
        assert "Lock acquisition failed" in (result.error or "")

    def test_runner_releases_lock_after_failure(
        self,
        sample_definition: WorkflowDefinition,
        memory_idempotency_registry: MemoryIdempotencyRegistry,
    ) -> None:
        """After a failed run, the lock should be released for the next run."""
        # Use a guard that will let us control the lock
        provider = MemoryLockProvider()
        guard = WorkflowExecutionGuard(
            lock_provider=provider,
            lease_duration_s=300,
            refresh_interval_s=30,
            max_retries=0,
        )
        runner = WorkflowRunner(
            execution_guard=guard,
            idempotency_registry=memory_idempotency_registry,
        )

        # First run should succeed
        r1 = runner.run(sample_definition, initial_artifact={"data": "first"})
        assert r1.lock_status == "acquired"

        # Second run on same workflow should also succeed (lock was released)
        r2 = runner.run(sample_definition, initial_artifact={"data": "second"})
        assert r2.lock_status == "acquired"
        assert r2.overall_status == ExecutionStatus.SUCCESS.value


# ── Tests: ExecutionContext Lock Fields ────────────────────────────────


class TestExecutionContextLockFields:
    def test_context_created_with_lock_fields(
        self,
        sample_definition: WorkflowDefinition,
    ) -> None:
        """Verify ExecutionContext can be constructed with lock fields."""
        from src.workflow_runtime.contracts.execution_context import ExecutionContext
        from src.workflow_runtime.locking.models import LockAcquisition

        lock = LockAcquisition(
            lock_id="test_wf",
            holder_id="holder-1",
            acquired_at="2026-06-03T08:00:00",
            expires_at="2026-06-03T08:05:00",
            lease_duration_s=300,
        )

        ctx = ExecutionContext(
            pipeline_run_id="run-1",
            workspace_id="ws-1",
            workflow_id="wf-1",
            started_at="2026-06-03T08:00:00",
            lock_acquisition=lock,
            idempotency_key="wf-1-scheduled-2026-06-03T08:00",
        )

        assert ctx.lock_acquisition is not None
        assert ctx.lock_acquisition.lock_id == "test_wf"
        assert ctx.idempotency_key == "wf-1-scheduled-2026-06-03T08:00"
        assert ctx.pipeline_run_id == "run-1"

    def test_context_defaults_to_none(self) -> None:
        """Verify ExecutionContext defaults for lock fields are None."""
        from src.workflow_runtime.contracts.execution_context import ExecutionContext

        ctx = ExecutionContext(
            pipeline_run_id="run-1",
            workspace_id="ws-1",
            workflow_id="wf-1",
            started_at="2026-06-03T08:00:00",
        )

        assert ctx.lock_acquisition is None
        assert ctx.idempotency_key is None