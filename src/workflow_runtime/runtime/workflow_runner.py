"""Sequential workflow execution runner — the core orchestration entry point."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.core.execution.status import ExecutionStatus
from src.workflow_runtime.contracts.execution_context import ExecutionContext
from src.workflow_runtime.contracts.workflow_definition import WorkflowDefinition
from src.workflow_runtime.contracts.workflow_result import StageResult, WorkflowResult
from src.workflow_runtime.dag.builder import DAGBuilder
from src.workflow_runtime.dsl.workflow_validator import WorkflowValidator
from src.workflow_runtime.locking.execution_guard import WorkflowExecutionGuard
from src.workflow_runtime.locking.exceptions import (
    LockAcquisitionError,
    IdempotencyRejectionError,
)
from src.workflow_runtime.locking.idempotency import WorkflowIdempotencyRegistry
from src.workflow_runtime.operations.base import BaseStage, STAGE_REGISTRY

logger = logging.getLogger(__name__)


def generate_idempotency_key(
    workflow_id: str,
    schedule_time: Optional[str] = None,
    scope: str = "scheduled",
) -> str:
    """Generate a deterministic idempotency key for a workflow invocation.

    For scheduled runs, the key incorporates the schedule time to enable
    per-slot deduplication. For manual runs without a schedule time,
    a unique key is generated per invocation.

    Args:
        workflow_id: The workflow identifier.
        schedule_time: Optional ISO-8601 timestamp for scheduled runs.
            If provided, the key will be deterministic for that time slot.
        scope: The trigger scope (default: "scheduled").

    Returns:
        A deterministic idempotency key string.
    """
    if schedule_time:
        # Truncate to minute precision for slot-based deduplication
        slot = schedule_time[:16]  # "2026-06-03T08:00"
        return f"{workflow_id}-{scope}-{slot}"
    return f"{workflow_id}-{scope}-{str(uuid.uuid4())}"


class WorkflowRunner:
    """Sequential workflow executor.

    Lifecycle for a single run:
      1. Validate workflow definition.
      2. Build topological execution order (DAG).
      3. Execute stages sequentially, passing artifacts through.
      4. Collect StageResults into WorkflowResult.
      5. Persist debug artifact (side effect, runtime layer only).
      6. Return WorkflowResult.

    When an ``execution_guard`` is configured, the lifecycle is extended:
      1. Validate workflow definition.
      2. Check idempotency key (if provided) — skip if already completed.
      3. Acquire execution lock.
      4. Build execution order and execute stages with periodic lease refresh.
      5. Release lock.
      6. Record idempotency outcome.
      7. Return WorkflowResult with lock_status populated.

    The runner is stateless — each ``run()`` call is independent.
    Locking is opt-in via the ``execution_guard`` parameter.
    """

    def __init__(
        self,
        debug_path: Optional[str] = None,
        execution_guard: Optional[WorkflowExecutionGuard] = None,
        idempotency_registry: Optional[WorkflowIdempotencyRegistry] = None,
    ):
        self._debug_path = Path(debug_path) if debug_path else None
        self._execution_guard = execution_guard
        self._idempotency_registry = idempotency_registry

    @property
    def execution_guard(self) -> Optional[WorkflowExecutionGuard]:
        """The configured ``WorkflowExecutionGuard``, if any."""
        return self._execution_guard

    @property
    def idempotency_registry(self) -> Optional[WorkflowIdempotencyRegistry]:
        """The configured ``WorkflowIdempotencyRegistry``, if any."""
        return self._idempotency_registry

    def run(
        self,
        definition: WorkflowDefinition,
        initial_artifact: Any = None,
        metadata: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> WorkflowResult:
        """Execute a workflow definition sequentially.

        Args:
            definition: Validated workflow definition.
            initial_artifact: Optional starting artifact (e.g., external input).
            metadata: Optional metadata for execution context.
            idempotency_key: Optional idempotency key for deduplication.
                If provided and the key has already been completed, execution
                is skipped and a cached result is returned.

        Returns:
            A WorkflowResult containing all StageResults and lock status.
        """
        pipeline_run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat()

        # ── Idempotency Check ──────────────────────────────────────────
        # If guard is configured and idempotency_key provided, check
        # before any execution.
        if idempotency_key is not None and self._idempotency_registry is not None:
            existing = self._idempotency_registry.check(idempotency_key)
            if existing is not None and existing.status == "completed":
                logger.info(
                    "Idempotency key %r already completed (run=%s). Skipping.",
                    idempotency_key,
                    existing.pipeline_run_id,
                )
                return WorkflowResult(
                    workflow_id=definition.workflow_id,
                    pipeline_run_id=pipeline_run_id,
                    workspace_id=definition.workspace_id,
                    overall_status=ExecutionStatus.SUCCESS.value,
                    started_at=started_at,
                    completed_at=started_at,
                    idempotency_key=idempotency_key,
                    lock_status="rejected_duplicate",
                )

        # ── Lock Acquisition ───────────────────────────────────────────
        # If guard is configured, acquire the execution lock. This
        # serializes concurrent runs of the same workflow_id.
        lock_acq = None
        if self._execution_guard is not None:
            try:
                lock_result, lock_acq = self._execution_guard.execute(
                    workflow_id=definition.workflow_id,
                    holder_id=pipeline_run_id,
                    fn=lambda: self._run_stages(
                        definition=definition,
                        initial_artifact=initial_artifact,
                        metadata=metadata,
                        pipeline_run_id=pipeline_run_id,
                        started_at=started_at,
                        lock_acquisition=None,  # Set after we return
                        idempotency_key=idempotency_key,
                    ),
                    idempotency_key=idempotency_key,
                    lease_duration_s=None,  # Use default from guard
                )
            except LockAcquisitionError as e:
                logger.warning(
                    "Lock acquisition failed for workflow_id=%s: %s",
                    definition.workflow_id,
                    e,
                )
                return WorkflowResult(
                    workflow_id=definition.workflow_id,
                    pipeline_run_id=pipeline_run_id,
                    workspace_id=definition.workspace_id,
                    overall_status=ExecutionStatus.FAILED.value,
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    error=str(e),
                    idempotency_key=idempotency_key,
                    lock_status="rejected_busy",
                )
            except IdempotencyRejectionError as e:
                logger.info(
                    "Idempotency key %r rejected: %s",
                    idempotency_key,
                    e,
                )
                return WorkflowResult(
                    workflow_id=definition.workflow_id,
                    pipeline_run_id=pipeline_run_id,
                    workspace_id=definition.workspace_id,
                    overall_status=ExecutionStatus.SUCCESS.value,
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    idempotency_key=idempotency_key,
                    lock_status="rejected_duplicate",
                )

            # If lock_result is None and lock_acq is None, execution was
            # skipped by the guard's idempotency check.
            if lock_result is None and lock_acq is None:
                return WorkflowResult(
                    workflow_id=definition.workflow_id,
                    pipeline_run_id=pipeline_run_id,
                    workspace_id=definition.workspace_id,
                    overall_status=ExecutionStatus.SUCCESS.value,
                    started_at=started_at,
                    completed_at=started_at,
                    idempotency_key=idempotency_key,
                    lock_status="rejected_duplicate",
                )

            # lock_result contains the WorkflowResult from _run_stages
            workflow_result = lock_result
            # Update with lock acquisition info
            object.__setattr__(workflow_result, "lock_status", "acquired")
            if idempotency_key:
                object.__setattr__(
                    workflow_result, "idempotency_key", idempotency_key
                )
            return workflow_result

        # ── No Guard Configured (Original Behaviour) ───────────────────
        workflow_result = self._run_stages(
            definition=definition,
            initial_artifact=initial_artifact,
            metadata=metadata,
            pipeline_run_id=pipeline_run_id,
            started_at=started_at,
            lock_acquisition=None,
            idempotency_key=idempotency_key,
        )
        return workflow_result

    def _run_stages(
        self,
        *,
        definition: WorkflowDefinition,
        initial_artifact: Any,
        metadata: Optional[Dict[str, Any]],
        pipeline_run_id: str,
        started_at: str,
        lock_acquisition: Any,
        idempotency_key: Optional[str],
    ) -> WorkflowResult:
        """Execute workflow stages and build result.

        This is the core execution logic, shared between locked and
        unlocked execution paths.
        """
        # 1. Validate
        WorkflowValidator.validate_or_raise(definition)

        # 2. Build execution order
        stages = DAGBuilder.build(definition)

        # 3. Prepare context
        context = ExecutionContext(
            pipeline_run_id=pipeline_run_id,
            workspace_id=definition.workspace_id,
            workflow_id=definition.workflow_id,
            started_at=started_at,
            metadata=metadata or {},
            debug_path=str(self._debug_path) if self._debug_path else None,
            lock_acquisition=lock_acquisition,
            idempotency_key=idempotency_key,
        )

        # 4. Execute stages sequentially
        stage_results: List[StageResult] = []
        current_artifact = initial_artifact

        for stage_def in stages:
            if stage_def.type not in STAGE_REGISTRY:
                stage_results.append(
                    StageResult(
                        stage_name=stage_def.name,
                        status=ExecutionStatus.FAILED.value,
                        error=f"Unknown stage type: '{stage_def.type}'. "
                        f"Valid types: {', '.join(sorted(STAGE_REGISTRY.keys()))}.",
                    )
                )
                break  # fail-fast

            stage_cls = STAGE_REGISTRY[stage_def.type]
            stage: BaseStage = stage_cls(config=stage_def.config)

            result: StageResult = stage.run(
                input_artifact=current_artifact,
                context=context,
            )
            stage_results.append(result)

            if result.status == ExecutionStatus.FAILED.value:
                break  # fail-fast

            current_artifact = result.output_artifact

        # 5. Build final result
        completed_at = datetime.now(timezone.utc).isoformat()
        overall_status = (
            ExecutionStatus.SUCCESS.value
            if all(r.status == ExecutionStatus.SUCCESS.value for r in stage_results)
            else ExecutionStatus.FAILED.value
        )
        errors = [r.error for r in stage_results if r.error]
        workflow_result = WorkflowResult(
            workflow_id=definition.workflow_id,
            pipeline_run_id=pipeline_run_id,
            workspace_id=definition.workspace_id,
            stage_results=stage_results,
            overall_status=overall_status,
            started_at=started_at,
            completed_at=completed_at,
            error=errors[0] if errors else None,
            idempotency_key=idempotency_key,
            lock_status=(
                "acquired" if lock_acquisition is not None else "not_locked"
            ),
        )

        # 6. Debug artifact (side effect — runtime layer only)
        if self._debug_path:
            self._persist_debug_artifact(workflow_result)

        return workflow_result

    def _persist_debug_artifact(self, result: WorkflowResult) -> None:
        """Write a complete workflow execution artifact to disk."""
        self._debug_path.mkdir(parents=True, exist_ok=True)
        artifact_path = self._debug_path / f"workflow_{result.pipeline_run_id}.json"
        artifact_path.write_text(result.to_json(), encoding="utf-8")