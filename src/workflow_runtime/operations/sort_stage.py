"""Workflow stage for deterministic stable sorting."""

from __future__ import annotations

import time
from typing import Any

from src.core.execution.status import ExecutionStatus
from src.transforms.contracts import SortPlan
from src.transforms.sorting import sort_data
from src.workflow_runtime.contracts.execution_context import ExecutionContext
from src.workflow_runtime.contracts.workflow_result import StageResult
from src.workflow_runtime.operations.base import BaseStage, STAGE_REGISTRY
from src.workflow_runtime.operations.tabular_artifact_adapter import to_dataframe


class SortStage(BaseStage):
    """Sort a supported tabular artifact using a versioned plan."""

    def run(self, input_artifact: Any, context: ExecutionContext) -> StageResult:
        start = time.monotonic()
        try:
            if "plan" not in self._config:
                raise ValueError("SortStage config requires 'plan'.")
            plan_payload = self._config["plan"]
            plan = plan_payload if isinstance(plan_payload, SortPlan) else SortPlan.from_dict(plan_payload)
            frame = to_dataframe(input_artifact)
            output = sort_data(frame, plan)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="sort",
                status=ExecutionStatus.SUCCESS.value,
                output_artifact=output,
                duration_ms=elapsed_ms,
                metadata={
                    "sort_keys": [key.field for key in plan.keys],
                    "operation_count": len(plan.keys),
                    "rows_in": len(frame),
                    "rows_out": len(output),
                },
            )
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="sort",
                status=ExecutionStatus.FAILED.value,
                duration_ms=elapsed_ms,
                error=str(exc),
            )


STAGE_REGISTRY["sort"] = SortStage

