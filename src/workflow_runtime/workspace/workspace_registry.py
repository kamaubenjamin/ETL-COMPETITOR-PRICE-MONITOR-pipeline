"""File-based workspace registry with tenant isolation."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from src.workflow_runtime.contracts.workflow_definition import WorkflowDefinition
from src.workflow_runtime.dsl.workflow_parser import WorkflowParser
from src.workflow_runtime.dsl.workflow_validator import WorkflowValidator


class WorkspaceRegistry:
    """Loads and indexes workflow definitions from a file-based workspace directory.

    Directory structure::

        workspaces/
        ├── quickmart/
        │   ├── workflows/
        │   │   └── detergents_monitoring.json
        │   └── workspace.json
        ├── shared/
        │   ├── templates/
        │   └── canonical_products.json
        └── ...

    v1 uses flat file loading — no database, no caching layer.
    """

    def __init__(self, workspaces_root: str):
        self._root = Path(workspaces_root)

    def list_workspaces(self) -> List[str]:
        """List all workspace IDs found in the root directory."""
        if not self._root.exists():
            return []
        return sorted(
            d.name for d in self._root.iterdir() if d.is_dir() and not d.name.startswith("_")
        )

    def list_workflows(self, workspace_id: str) -> List[str]:
        """List all workflow IDs for a given workspace."""
        workflow_dir = self._root / workspace_id / "workflows"
        if not workflow_dir.exists():
            return []
        return sorted(
            f.stem for f in workflow_dir.iterdir() if f.suffix == ".json"
        )

    def load_workflow(self, workspace_id: str, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Load a single workflow definition from file.

        Returns None if the file does not exist.
        """
        path = self._root / workspace_id / "workflows" / f"{workflow_id}.json"
        if not path.exists():
            return None
        definition = WorkflowParser.parse_file(str(path))
        # Validate and return
        WorkflowValidator.validate_or_raise(definition)
        return definition

    def load_all_workflows(self, workspace_id: str) -> List[WorkflowDefinition]:
        """Load all workflow definitions for a workspace, skipping invalid ones."""
        workflow_dir = self._root / workspace_id / "workflows"
        if not workflow_dir.exists():
            return []

        definitions: List[WorkflowDefinition] = []
        for path in sorted(workflow_dir.glob("*.json")):
            try:
                definition = WorkflowParser.parse_file(str(path))
                WorkflowValidator.validate_or_raise(definition)
                definitions.append(definition)
            except (ValueError, KeyError) as exc:
                # Skip invalid workflow definitions silently
                continue
        return definitions