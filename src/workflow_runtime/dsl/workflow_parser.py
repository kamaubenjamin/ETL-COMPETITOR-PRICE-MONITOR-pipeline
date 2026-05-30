"""Parses workflow JSON definitions into typed WorkflowDefinition objects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from src.workflow_runtime.contracts.workflow_definition import (
    StageDefinition,
    WorkflowDefinition,
)


class WorkflowParser:
    """Parses workflow JSON files or dicts into typed WorkflowDefinition objects.

    No validation is performed here — use ``WorkflowValidator`` for schema checks.
    """

    @staticmethod
    def parse_dict(data: Dict[str, Any]) -> WorkflowDefinition:
        """Parse a workflow dictionary into a typed WorkflowDefinition."""
        stages_data: List[Dict[str, Any]] = data.get("stages", [])
        stages = [
            StageDefinition(
                name=s["name"],
                type=s["type"],
                depends_on=list(s.get("depends_on", [])),
                config=dict(s.get("config", {})),
                metadata=dict(s.get("metadata", {})),
            )
            for s in stages_data
        ]

        return WorkflowDefinition(
            workflow_id=data["workflow_id"],
            name=data.get("name", data["workflow_id"]),
            version=data.get("version", "1.0.0"),
            workspace_id=data.get("workspace_id", "default"),
            enabled=bool(data.get("enabled", True)),
            description=data.get("description", ""),
            stages=stages,
            metadata=dict(data.get("metadata", {})),
        )

    @staticmethod
    def parse_file(file_path: str) -> WorkflowDefinition:
        """Parse a workflow JSON file into a typed WorkflowDefinition."""
        path = Path(file_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        return WorkflowParser.parse_dict(data)

    @staticmethod
    def parse_json(json_str: str) -> WorkflowDefinition:
        """Parse a workflow JSON string into a typed WorkflowDefinition."""
        data = json.loads(json_str)
        return WorkflowParser.parse_dict(data)