"""Immutable privacy-safe Workflow Studio validation result contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .contracts import StudioContract, bounded_text, optional_id, safe_code, stable_id


class ValidationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    BLOCKING = "blocking"


class ValidationLayer(str, Enum):
    SCHEMA = "schema"
    SEMANTIC = "semantic"
    DEPENDENCY = "dependency"
    OPERATION_COMPATIBILITY = "operation_compatibility"
    PATH = "path"
    SECURITY = "security"
    PUBLICATION = "publication"
    LEGACY_COMPATIBILITY = "legacy_compatibility"


class LegacyCompatibilityStatus(str, Enum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


@dataclass(frozen=True, slots=True)
class WorkflowValidationIssue(StudioContract):
    code: str
    severity: ValidationSeverity
    layer: ValidationLayer
    summary: str
    rule_id: str | None = None
    action_id: str | None = None
    path: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", safe_code(self.code, "issue code"))
        try:
            severity = self.severity if isinstance(self.severity, ValidationSeverity) else ValidationSeverity(self.severity)
            layer = self.layer if isinstance(self.layer, ValidationLayer) else ValidationLayer(self.layer)
        except (TypeError, ValueError) as error:
            raise ValueError("validation issue classification is unsupported") from error
        object.__setattr__(self, "severity", severity)
        object.__setattr__(self, "layer", layer)
        object.__setattr__(self, "summary", bounded_text(self.summary, "issue summary", maximum=256))
        object.__setattr__(self, "rule_id", optional_id(self.rule_id, "rule_id"))
        object.__setattr__(self, "action_id", optional_id(self.action_id, "action_id"))
        if self.path is not None:
            object.__setattr__(self, "path", bounded_text(self.path, "issue path", maximum=128))


@dataclass(frozen=True, slots=True)
class DependencyValidationResult(StudioContract):
    valid: bool
    ordered_rule_ids: tuple[str, ...]
    cycle_member_ids: tuple[str, ...]
    issues: tuple[WorkflowValidationIssue, ...]

    def __post_init__(self) -> None:
        _booleans(self.valid)
        object.__setattr__(self, "ordered_rule_ids", _ids(self.ordered_rule_ids, "ordered_rule_ids"))
        object.__setattr__(self, "cycle_member_ids", _ids(self.cycle_member_ids, "cycle_member_ids"))
        object.__setattr__(self, "issues", _issues(self.issues))


@dataclass(frozen=True, slots=True)
class OperationCompatibilityResult(StudioContract):
    rule_id: str
    action_id: str
    operation_name: str
    operation_version: str
    structurally_valid: bool
    preview_eligible: bool
    publication_eligible: bool
    required_features: tuple[str, ...]
    missing_features: tuple[str, ...]
    runtime_mapping: str | None
    issues: tuple[WorkflowValidationIssue, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", stable_id(self.rule_id, "rule_id"))
        object.__setattr__(self, "action_id", stable_id(self.action_id, "action_id"))
        object.__setattr__(self, "operation_name", safe_code(self.operation_name, "operation_name"))
        object.__setattr__(self, "operation_version", bounded_text(self.operation_version, "operation_version", maximum=32))
        _booleans(self.structurally_valid, self.preview_eligible, self.publication_eligible)
        object.__setattr__(self, "required_features", _codes(self.required_features, "required_features"))
        object.__setattr__(self, "missing_features", _codes(self.missing_features, "missing_features"))
        if self.runtime_mapping is not None:
            object.__setattr__(self, "runtime_mapping", safe_code(self.runtime_mapping, "runtime_mapping"))
        object.__setattr__(self, "issues", _issues(self.issues))


@dataclass(frozen=True, slots=True)
class RuleValidationResult(StudioContract):
    rule_id: str
    valid: bool
    preview_eligible: bool
    publication_eligible: bool
    issues: tuple[WorkflowValidationIssue, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", stable_id(self.rule_id, "rule_id"))
        _booleans(self.valid, self.preview_eligible, self.publication_eligible)
        object.__setattr__(self, "issues", _issues(self.issues))


@dataclass(frozen=True, slots=True)
class WorkflowValidationResult(StudioContract):
    workflow_id: str
    version_id: str
    structurally_valid: bool
    preview_eligible: bool
    test_ready: bool
    publication_eligible: bool
    publication_blocked: bool
    ordered_rule_ids: tuple[str, ...]
    issues: tuple[WorkflowValidationIssue, ...]
    rule_results: tuple[RuleValidationResult, ...]
    dependency_result: DependencyValidationResult
    operation_results: tuple[OperationCompatibilityResult, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "workflow_id", stable_id(self.workflow_id, "workflow_id"))
        object.__setattr__(self, "version_id", stable_id(self.version_id, "version_id"))
        _booleans(self.structurally_valid, self.preview_eligible, self.test_ready, self.publication_eligible, self.publication_blocked)
        object.__setattr__(self, "ordered_rule_ids", _ids(self.ordered_rule_ids, "ordered_rule_ids"))
        object.__setattr__(self, "issues", _issues(self.issues))
        if not isinstance(self.dependency_result, DependencyValidationResult):
            raise ValueError("dependency_result must be modeled")
        if not isinstance(self.rule_results, (tuple, list)) or not all(isinstance(item, RuleValidationResult) for item in self.rule_results):
            raise ValueError("rule_results must be modeled")
        if not isinstance(self.operation_results, (tuple, list)) or not all(isinstance(item, OperationCompatibilityResult) for item in self.operation_results):
            raise ValueError("operation_results must be modeled")
        object.__setattr__(self, "rule_results", tuple(self.rule_results))
        object.__setattr__(self, "operation_results", tuple(self.operation_results))


def _booleans(*values: bool) -> None:
    if not all(isinstance(value, bool) for value in values):
        raise ValueError("validation readiness values must be booleans")


def _ids(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)) or len(values) > 100:
        raise ValueError(f"{field_name} must be bounded")
    return tuple(stable_id(item, field_name) for item in values)


def _codes(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)) or len(values) > 32:
        raise ValueError(f"{field_name} must be bounded")
    return tuple(safe_code(item, field_name) for item in values)


def _issues(values: tuple[WorkflowValidationIssue, ...]) -> tuple[WorkflowValidationIssue, ...]:
    if not isinstance(values, (tuple, list)) or len(values) > 500 or not all(isinstance(item, WorkflowValidationIssue) for item in values):
        raise ValueError("issues must be a bounded modeled sequence")
    return tuple(values)
