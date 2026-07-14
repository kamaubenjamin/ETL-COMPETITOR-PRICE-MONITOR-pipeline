"""Stable standard-library dependency validation and topological ordering."""

from __future__ import annotations

from dataclasses import dataclass
import heapq

from .contracts import StudioContract, stable_id
from .definitions import RuleDefinition
from .validation_errors import ValidationIssueCode, validation_issue
from .validation_results import DependencyValidationResult, ValidationLayer, ValidationSeverity


@dataclass(frozen=True, slots=True)
class RuleDependencyNode(StudioContract):
    rule_id: str
    dependencies: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", stable_id(self.rule_id, "rule_id"))
        if not isinstance(self.dependencies, (tuple, list)) or len(self.dependencies) > 100:
            raise ValueError("dependencies must be a bounded sequence")
        object.__setattr__(self, "dependencies", tuple(stable_id(item, "dependency") for item in self.dependencies))


def validate_dependencies(rules: tuple[RuleDefinition | RuleDependencyNode, ...] | list[RuleDefinition | RuleDependencyNode]) -> DependencyValidationResult:
    if not isinstance(rules, (tuple, list)) or len(rules) > 100:
        raise ValueError("rules must be a bounded sequence")
    nodes = tuple(RuleDependencyNode(item.rule_id, item.dependencies) for item in rules)
    issues = []
    identifiers = [node.rule_id for node in nodes]
    known = set(identifiers)
    duplicate_ids = {item for item in identifiers if identifiers.count(item) > 1}
    for rule_id in sorted(duplicate_ids):
        issues.append(validation_issue(ValidationIssueCode.DUPLICATE_RULE_ID, ValidationSeverity.BLOCKING, ValidationLayer.SCHEMA, rule_id=rule_id))

    graph: dict[str, set[str]] = {rule_id: set() for rule_id in known}
    dependents: dict[str, set[str]] = {rule_id: set() for rule_id in known}
    for node in sorted(nodes, key=lambda item: item.rule_id):
        duplicate_dependencies = {item for item in node.dependencies if node.dependencies.count(item) > 1}
        if duplicate_dependencies:
            issues.append(validation_issue(ValidationIssueCode.DUPLICATE_DEPENDENCY, ValidationSeverity.BLOCKING, ValidationLayer.DEPENDENCY, rule_id=node.rule_id))
        for dependency in sorted(set(node.dependencies)):
            if dependency == node.rule_id:
                issues.append(validation_issue(ValidationIssueCode.SELF_DEPENDENCY, ValidationSeverity.BLOCKING, ValidationLayer.DEPENDENCY, rule_id=node.rule_id))
            elif dependency not in known:
                issues.append(validation_issue(ValidationIssueCode.MISSING_DEPENDENCY, ValidationSeverity.BLOCKING, ValidationLayer.DEPENDENCY, rule_id=node.rule_id))
            else:
                graph[node.rule_id].add(dependency)
                dependents[dependency].add(node.rule_id)

    indegree = {rule_id: len(dependencies) for rule_id, dependencies in graph.items()}
    ready = [rule_id for rule_id, count in indegree.items() if count == 0]
    heapq.heapify(ready)
    ordered = []
    while ready:
        current = heapq.heappop(ready)
        ordered.append(current)
        for dependent in sorted(dependents[current]):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                heapq.heappush(ready, dependent)
    cycle_members = _cycle_members(graph)
    if cycle_members:
        issues.append(validation_issue(ValidationIssueCode.DEPENDENCY_CYCLE, ValidationSeverity.BLOCKING, ValidationLayer.DEPENDENCY))
    valid = not issues
    return DependencyValidationResult(valid, tuple(ordered) if valid else (), cycle_members, tuple(issues))


def _cycle_members(graph: dict[str, set[str]]) -> tuple[str, ...]:
    index = 0
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    members: set[str] = set()

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for dependency in sorted(graph[node]):
            if dependency not in indices:
                visit(dependency)
                lowlinks[node] = min(lowlinks[node], lowlinks[dependency])
            elif dependency in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[dependency])
        if lowlinks[node] == indices[node]:
            component = []
            while True:
                current = stack.pop()
                on_stack.remove(current)
                component.append(current)
                if current == node:
                    break
            if len(component) > 1 or node in graph[node]:
                members.update(component)

    for node in sorted(graph):
        if node not in indices:
            visit(node)
    return tuple(sorted(members))
