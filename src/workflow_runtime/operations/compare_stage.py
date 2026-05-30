"""Compare stage — price comparison between sources."""

from __future__ import annotations

import time
from typing import Any

from src.core.execution.status import ExecutionStatus
from src.workflow_runtime.contracts.execution_context import ExecutionContext
from src.workflow_runtime.contracts.workflow_result import StageResult
from src.workflow_runtime.operations.base import BaseStage, STAGE_REGISTRY


class CompareStage(BaseStage):
    """Performs price comparison analysis on matched products.

    Stage config:
        - comparison_type (str, optional): Type of comparison (supplier_vs_market, cross_source).
    """

    def run(self, input_artifact: Any, context: ExecutionContext) -> StageResult:
        comparison_type: str = self._config.get("comparison_type", "cross_source")

        start = time.monotonic()
        try:
            output = {
                "input_artifact": input_artifact,
                "comparison_type": comparison_type,
                "comparisons": [],
            }
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="compare",
                status=ExecutionStatus.SUCCESS.value,
                output_artifact=output,
                duration_ms=elapsed_ms,
                metadata={"comparison_type": comparison_type},
            )
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="compare",
                status=ExecutionStatus.FAILED.value,
                error=str(exc),
                duration_ms=elapsed_ms,
            )


STAGE_REGISTRY["compare"] = CompareStage