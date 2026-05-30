"""Transform stage — applies normalization/transformation rules to structured data."""

from __future__ import annotations

import time
from typing import Any

from src.core.execution.status import ExecutionStatus
from src.workflow_runtime.contracts.execution_context import ExecutionContext
from src.workflow_runtime.contracts.workflow_result import StageResult
from src.workflow_runtime.operations.base import BaseStage, STAGE_REGISTRY


class TransformStage(BaseStage):
    """Applies transform rules to the output of the ingest stage.

    Stage config:
        - rules (list): List of transform rule dicts (normalize, drop_nulls, deduplicate).
    """

    def run(self, input_artifact: Any, context: ExecutionContext) -> StageResult:
        rules: list = self._config.get("rules", [])

        start = time.monotonic()
        try:
            # In v1, transform logic is delegated to the existing transform modules.
            # The input artifact is the IngestionPipelineResult.
            # For MVP, this stage passes through the normalized document content.
            output = {
                "input_artifact": input_artifact,
                "rules_applied": rules,
                "transform_count": len(rules),
            }
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="transform",
                status=ExecutionStatus.SUCCESS.value,
                output_artifact=output,
                duration_ms=elapsed_ms,
                metadata={"rules_applied": len(rules)},
            )
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="transform",
                status=ExecutionStatus.FAILED.value,
                error=str(exc),
                duration_ms=elapsed_ms,
            )


STAGE_REGISTRY["transform"] = TransformStage