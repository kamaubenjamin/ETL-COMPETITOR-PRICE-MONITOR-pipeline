"""Workflow stage for deterministic tabular aggregation."""

from __future__ import annotations

import time
from typing import Any

from src.core.execution.status import ExecutionStatus
from src.transforms.aggregation import aggregate_data
from src.transforms.contracts import AggregationPlan
from src.workflow_runtime.contracts.execution_context import ExecutionContext
from src.workflow_runtime.contracts.workflow_result import StageResult
from src.workflow_runtime.operations.base import BaseStage, STAGE_REGISTRY
from src.workflow_runtime.operations.tabular_artifact_adapter import to_dataframe


class AggregationStage(BaseStage):
    """Aggregate a supported tabular artifact using a versioned plan."""

    def run(self, input_artifact: Any, context: ExecutionContext) -> StageResult:
        start = time.monotonic()
        try:
            if "plan" not in self._config:
                raise ValueError("AggregationStage config requires 'plan'.")
            plan_payload = self._config["plan"]
            plan = plan_payload if isinstance(plan_payload, AggregationPlan) else AggregationPlan.from_dict(plan_payload)
            frame = to_dataframe(input_artifact)
            output = aggregate_data(frame, plan)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="aggregate",
                status=ExecutionStatus.SUCCESS.value,
                output_artifact=output,
                duration_ms=elapsed_ms,
                metadata={
                    "aggregate_ids": [item.output for item in plan.aggregations],
                    "group_by": list(plan.group_by),
                    "operation_count": len(plan.aggregations),
                    "rows_in": len(frame),
                    "rows_out": len(output),
                },
            )
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="aggregate",
                status=ExecutionStatus.FAILED.value,
                duration_ms=elapsed_ms,
                error=str(exc),
            )


STAGE_REGISTRY["aggregate"] = AggregationStage

