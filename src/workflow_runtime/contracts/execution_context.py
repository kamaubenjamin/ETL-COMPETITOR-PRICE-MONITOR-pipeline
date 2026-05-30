"""Execution context passed to each operation at runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """Immutable context object passed to every stage operation.

    Created at pipeline start, never mutated during execution.
    """

    pipeline_run_id: str
    workspace_id: str
    workflow_id: str
    started_at: str  # ISO timestamp
    metadata: Dict[str, Any] = field(default_factory=dict)
    debug_path: Optional[str] = None