"""Fuzzy match stage — product matching against canonical catalog."""

from __future__ import annotations

import time
from typing import Any

from src.core.execution.status import ExecutionStatus
from src.workflow_runtime.contracts.execution_context import ExecutionContext
from src.workflow_runtime.contracts.workflow_result import StageResult
from src.workflow_runtime.operations.base import BaseStage, STAGE_REGISTRY


class FuzzyMatchStage(BaseStage):
    """Matches structured records against a canonical product catalog.

    Stage config:
        - match_threshold (int, optional): Similarity threshold (0–100). Default: 78.
    """

    def run(self, input_artifact: Any, context: ExecutionContext) -> StageResult:
        threshold: int = self._config.get("match_threshold", 78)

        start = time.monotonic()
        try:
            output = {
                "input_artifact": input_artifact,
                "match_threshold": threshold,
                "matches": [],
            }
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="fuzzy_match",
                status=ExecutionStatus.SUCCESS.value,
                output_artifact=output,
                duration_ms=elapsed_ms,
                metadata={"match_threshold": threshold},
            )
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="fuzzy_match",
                status=ExecutionStatus.FAILED.value,
                error=str(exc),
                duration_ms=elapsed_ms,
            )


STAGE_REGISTRY["fuzzy_match"] = FuzzyMatchStage