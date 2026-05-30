"""Stage and workflow execution result contracts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.core.execution.status import ExecutionStatus


@dataclass(frozen=True, slots=True)
class StageResult:
    """Immutable output of a single workflow stage execution."""

    stage_name: str
    status: str  # ExecutionStatus value
    output_artifact: Optional[Any] = None
    duration_ms: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_name": self.stage_name,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "has_output": self.output_artifact is not None,
            "metadata": self.metadata,
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)


@dataclass(frozen=True, slots=True)
class WorkflowResult:
    """Immutable aggregate result of a completed workflow execution."""

    workflow_id: str
    pipeline_run_id: str
    workspace_id: str
    stage_results: List[StageResult] = field(default_factory=list)
    overall_status: str = ExecutionStatus.PENDING.value
    started_at: str = ""
    completed_at: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "pipeline_run_id": self.pipeline_run_id,
            "workspace_id": self.workspace_id,
            "overall_status": self.overall_status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "stage_count": len(self.stage_results),
            "stage_results": [s.to_dict() for s in self.stage_results],
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)