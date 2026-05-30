"""Builds a topological execution order from workflow stage dependencies."""

from __future__ import annotations

from collections import deque
from typing import Dict, List, Set

from src.workflow_runtime.contracts.workflow_definition import (
    StageDefinition,
    WorkflowDefinition,
)


class DAGBuilder:
    """Constructs a deterministic sequential execution order from stage dependencies.

    Uses Kahn's algorithm for topological sorting. Detects cycles.
    """

    @staticmethod
    def build(definition: WorkflowDefinition) -> List[StageDefinition]:
        """Return stages in topological execution order.

        Args:
            definition: A validated workflow definition.

        Returns:
            A list of StageDefinition objects in execution order.

        Raises:
            ValueError: If the dependency graph contains a cycle or missing stages.
        """
        stages = {s.name: s for s in definition.stages}
        in_degree: Dict[str, int] = {s.name: 0 for s in definition.stages}
        adjacency: Dict[str, List[str]] = {s.name: [] for s in definition.stages}

        # Build adjacency and in-degree
        for stage in definition.stages:
            for dep in stage.depends_on:
                if dep in adjacency:
                    adjacency[dep].append(stage.name)
                in_degree[stage.name] = in_degree.get(stage.name, 0) + 1

        # Kahn's algorithm
        queue: deque = deque()
        for name, degree in in_degree.items():
            if degree == 0:
                queue.append(name)

        sorted_names: List[str] = []
        while queue:
            name = queue.popleft()
            sorted_names.append(name)
            for neighbor in adjacency[name]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_names) != len(definition.stages):
            cycle_nodes = set(stages.keys()) - set(sorted_names)
            raise ValueError(
                f"DAG cycle detected involving stages: {', '.join(sorted(cycle_nodes))}. "
                "Check depends_on references for circular dependencies."
            )

        return [stages[name] for name in sorted_names]