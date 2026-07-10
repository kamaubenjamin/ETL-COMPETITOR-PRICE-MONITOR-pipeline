"""Workflow stage for deterministic tabular data validation."""

from __future__ import annotations

import time
from copy import deepcopy
from typing import Any

import pandas as pd

from src.core.execution.status import ExecutionStatus
from src.transforms.contracts import ValidationPlan
from src.transforms.regex_registry import RegexRegistry
from src.transforms.validation import validate_data
from src.workflow_runtime.contracts.execution_context import ExecutionContext
from src.workflow_runtime.contracts.workflow_result import StageResult
from src.workflow_runtime.operations.base import BaseStage, STAGE_REGISTRY
from src.workflow_runtime.operations.tabular_artifact_adapter import to_dataframe


def _copy_artifact(input_artifact: Any) -> Any:
    if isinstance(input_artifact, pd.DataFrame):
        return input_artifact.copy(deep=True)
    return deepcopy(input_artifact)


class ValidationStage(BaseStage):
    """Validate tabular data using a versioned validation plan."""

    def run(self, input_artifact: Any, context: ExecutionContext) -> StageResult:
        start = time.monotonic()
        try:
            if "plan" not in self._config:
                raise ValueError("ValidationStage config requires 'plan'.")
            plan_payload = self._config["plan"]
            plan = plan_payload if isinstance(plan_payload, ValidationPlan) else ValidationPlan.from_dict(plan_payload)
            regex_registry = RegexRegistry.from_dicts(self._config.get("regex_definitions"))
            frame = to_dataframe(input_artifact)
            validation_result = validate_data(frame, plan, regex_registry=regex_registry)
            metadata = {"validation": validation_result.to_dict()}
            elapsed_ms = int((time.monotonic() - start) * 1000)

            if plan.failure_policy == "fail_stage" and validation_result.error_count > 0:
                return StageResult(
                    stage_name="validate_data",
                    status=ExecutionStatus.FAILED.value,
                    duration_ms=elapsed_ms,
                    error=f"Data validation failed with {validation_result.error_count} error issue(s).",
                    metadata=metadata,
                )

            return StageResult(
                stage_name="validate_data",
                status=ExecutionStatus.SUCCESS.value,
                output_artifact=_copy_artifact(input_artifact),
                duration_ms=elapsed_ms,
                metadata=metadata,
            )
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="validate_data",
                status=ExecutionStatus.FAILED.value,
                duration_ms=elapsed_ms,
                error=str(exc),
            )


STAGE_REGISTRY["validate_data"] = ValidationStage

