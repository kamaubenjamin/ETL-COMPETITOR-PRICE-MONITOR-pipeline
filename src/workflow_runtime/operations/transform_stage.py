"""Transform stage — applies normalization/transformation rules to structured data."""

from __future__ import annotations

import time
from typing import Any

from src.core.execution.status import ExecutionStatus
from src.transforms.contracts import TransformationPlan
from src.transforms.pipeline import TransformationPipeline
from src.transforms.regex_registry import RegexRegistry
from src.workflow_runtime.contracts.execution_context import ExecutionContext
from src.workflow_runtime.contracts.workflow_result import StageResult
from src.workflow_runtime.operations.base import BaseStage, STAGE_REGISTRY
from src.workflow_runtime.operations.tabular_artifact_adapter import to_dataframe


class TransformStage(BaseStage):
    """Apply a strict transformation plan or backward-compatible legacy rules.

    Stage config:
        - plan (dict): Versioned deterministic transformation plan.
        - regex_definitions (list): Named patterns referenced by the plan.
        - rules (list): Legacy transformation rules.
    """

    def run(self, input_artifact: Any, context: ExecutionContext) -> StageResult:
        start = time.monotonic()
        try:
            if self._config == {"operation": "identity"}:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                return StageResult(
                    stage_name="transform",
                    status=ExecutionStatus.SUCCESS.value,
                    output_artifact=input_artifact,
                    duration_ms=elapsed_ms,
                    metadata={
                        "operation_ids": ["identity"],
                        "operation_count": 1,
                    },
                )

            if "plan" in self._config and "rules" in self._config:
                raise ValueError("TransformStage config must use either 'plan' or 'rules', not both.")

            frame = to_dataframe(input_artifact)
            rows_in = len(frame)
            pipeline = TransformationPipeline(frame)

            if "plan" in self._config:
                plan_payload = self._config["plan"]
                plan = (
                    plan_payload
                    if isinstance(plan_payload, TransformationPlan)
                    else TransformationPlan.from_dict(plan_payload)
                )
                regex_registry = RegexRegistry.from_dicts(self._config.get("regex_definitions"))
                output = pipeline.apply_plan(plan, regex_registry=regex_registry)
                operation_ids = [operation.id for operation in plan.operations]
            else:
                rules = self._config.get("rules", [])
                if not isinstance(rules, list):
                    raise TypeError("TransformStage legacy 'rules' must be a list.")
                output = pipeline.apply(rules)
                operation_ids = [
                    str(rule.get("id") or f"legacy-{index + 1}-{rule.get('type', 'unknown')}")
                    for index, rule in enumerate(rules)
                    if isinstance(rule, dict)
                ]

            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="transform",
                status=ExecutionStatus.SUCCESS.value,
                output_artifact=output,
                duration_ms=elapsed_ms,
                metadata={
                    "operation_ids": operation_ids,
                    "operation_count": len(operation_ids),
                    "rows_in": rows_in,
                    "rows_out": len(output),
                },
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
