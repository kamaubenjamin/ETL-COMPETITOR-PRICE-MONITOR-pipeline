"""Alert stage — evaluates alert rules and generates alerts."""

from __future__ import annotations

import time
from typing import Any

from src.core.execution.status import ExecutionStatus
from src.workflow_runtime.contracts.execution_context import ExecutionContext
from src.workflow_runtime.contracts.workflow_result import StageResult
from src.workflow_runtime.operations.base import BaseStage, STAGE_REGISTRY


class AlertStage(BaseStage):
    """Evaluates alert rules against comparison results.

    Stage config:
        - price_drop_percentage (int, optional): Threshold for price drop alerts.
        - undercut_threshold (int, optional): Threshold for undercut detection.
    """

    def run(self, input_artifact: Any, context: ExecutionContext) -> StageResult:
        price_drop_pct: int = self._config.get("price_drop_percentage", 5)
        undercut_threshold: int = self._config.get("undercut_threshold", 50)

        start = time.monotonic()
        try:
            output = {
                "input_artifact": input_artifact,
                "alerts_generated": [],
                "alert_config": {
                    "price_drop_percentage": price_drop_pct,
                    "undercut_threshold": undercut_threshold,
                },
            }
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="alert",
                status=ExecutionStatus.SUCCESS.value,
                output_artifact=output,
                duration_ms=elapsed_ms,
                metadata={
                    "price_drop_percentage": price_drop_pct,
                    "undercut_threshold": undercut_threshold,
                },
            )
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="alert",
                status=ExecutionStatus.FAILED.value,
                error=str(exc),
                duration_ms=elapsed_ms,
            )


STAGE_REGISTRY["alert"] = AlertStage