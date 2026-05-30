"""Sequential workflow execution runner — the core orchestration entry point."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.execution.status import ExecutionStatus
from src.workflow_runtime.contracts.execution_context import ExecutionContext
from src.workflow_runtime.contracts.workflow_definition import WorkflowDefinition
from src.workflow_runtime.contracts.workflow_result import StageResult, WorkflowResult
from src.workflow_runtime.dag.builder import DAGBuilder
from src.workflow_runtime.dsl.workflow_validator import WorkflowValidator
from src.workflow_runtime.operations.base import BaseStage, STAGE_REGISTRY


class WorkflowRunner:
    """Sequential workflow executor.

    Lifecycle for a single run:
      1. Validate workflow definition.
      2. Build topological execution order (DAG).
      3. Execute stages sequentially, passing artifacts through.
      4. Collect StageResults into WorkflowResult.
      5. Persist debug artifact (side effect, runtime layer only).
      6. Return WorkflowResult.

    The runner is stateless — each ``run()`` call is independent.
    """

    def __init__(self, debug_path: Optional[str] = None):
        self._debug_path = Path(debug_path) if debug_path else None

    def run(
        self,
        definition: WorkflowDefinition,
        initial_artifact: Any = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkflowResult:
        """Execute a workflow definition sequentially.

        Args:
            definition: Validated workflow definition.
            initial_artifact: Optional starting artifact (e.g., external input).
            metadata: Optional metadata for execution context.

        Returns:
            A WorkflowResult containing all StageResults.
        """
        # 1. Validate
        WorkflowValidator.validate_or_raise(definition)

        # 2. Build execution order
        stages = DAGBuilder.build(definition)

        # 3. Prepare context
        pipeline_run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat()
        context = ExecutionContext(
            pipeline_run_id=pipeline_run_id,
            workspace_id=definition.workspace_id,
            workflow_id=definition.workflow_id,
            started_at=started_at,
            metadata=metadata or {},
            debug_path=str(self._debug_path) if self._debug_path else None,
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