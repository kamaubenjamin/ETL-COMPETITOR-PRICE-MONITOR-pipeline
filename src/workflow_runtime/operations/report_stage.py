"""Report stage — generates output reports from pipeline results."""

from __future__ import annotations

import time
from typing import Any

from src.core.execution.status import ExecutionStatus
from src.workflow_runtime.contracts.execution_context import ExecutionContext
from src.workflow_runtime.contracts.workflow_result import StageResult
from src.workflow_runtime.operations.base import BaseStage, STAGE_REGISTRY


class ReportStage(BaseStage):
    """Generates output reports (CSV/JSON) from aggregated pipeline results.

    Stage config:
        - export_csv (bool, optional): Enable CSV export.
        - report_dir (str, optional): Output directory for reports.
    """

    def run(self, input_artifact: Any, context: ExecutionContext) -> StageResult:
        export_csv: bool = self._config.get("export_csv", False)
        report_dir: str = self._config.get("report_dir", "reports")

        start = time.monotonic()
        try:
            output = {
                "input_artifact": input_artifact,
                "reports_generated": [],
                "report_config": {
                    "export_csv": export_csv,
                    "report_dir": report_dir,
                },
            }
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="report",
                status=ExecutionStatus.SUCCESS.value,
                output_artifact=output,
                duration_ms=elapsed_ms,
                metadata={"export_csv": export_csv, "report_dir": report_dir},
            )
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return StageResult(
                stage_name="report",
                status=ExecutionStatus.FAILED.value,
                error=str(exc),
                duration_ms=elapsed_ms,
            )


STAGE_REGISTRY["report"] = ReportStage