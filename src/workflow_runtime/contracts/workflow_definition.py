"""Workflow and stage definition contracts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True, slots=True)
class StageDefinition:
    """A single stage in a workflow pipeline.

    Stages are orchestration definitions — they describe what to run.
    The runtime resolves the ``type`` field against the operation registry.
    """

    name: str
    type: str
    depends_on: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    """Immutable definition of a document processing workflow.

    Loaded from JSON, parsed by ``WorkflowParser``, validated by ``WorkflowValidator``.
    """

    workflow_id: str
    name: str
    version: str
    workspace_id: str
    enabled: bool
    description: str = ""
    stages: List[StageDefinition] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "version": self.version,
            "workspace_id": self.workspace_id,
            "enabled": self.enabled,
            "description": self.description,
            "stages": [s.to_dict() for s in self.stages],
            "metadata": self.metadata,
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)