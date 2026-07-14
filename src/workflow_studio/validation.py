"""Deterministic side-effect-free Workflow Studio validation service."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .compatibility import validate_action_compatibility
from .conditions import BooleanOperator, ConditionDefinition, ConditionGroup, ConditionOperator, NullPolicy
from .contracts import StudioContract
from .definitions import RuleDefinition, WorkflowDefinition, WorkflowVersion
from .dependencies import validate_dependencies
from .path_validation import validate_logical_path
from .ports import WorkflowOperationCatalogPort
from .validation_errors import ValidationIssueCode, validation_issue
from .validation_results import (
    RuleValidationResult,
    ValidationLayer,
    ValidationSeverity,
    WorkflowValidationIssue,
    WorkflowValidationResult,
)


@dataclass(frozen=True, slots=True)
class ValidationPolicyFacts(StudioContract):
    available_features: tuple[str, ...] = ()
    require_test_evidence: bool = False
    test_evidence_passed: bool = False
    require_approval_evidence: bool = False
    approval_evidence_present: bool = False
    legacy_manual_review_required: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.available_features, (tuple, list)) or len(self.available_features) > 32:
            raise ValueError("available_features must be bounded")
        features = tuple(sorted(set(self.available_features)))
        if not all(isinstance(item, str) and item.isidentifier() and item.islower() for item in features):
            raise ValueError("available_features must contain safe labels")
        for field_name in (
            "require_test_evidence", "test_evidence_passed", "require_approval_evidence",
            "approval_evidence_present", "legacy_manual_review_required",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise ValueError(f"{field_name} must be a boolean")
        object.__setattr__(self, "available_features", features)


class WorkflowValidationService:
    def __init__(self, catalog: WorkflowOperationCatalogPort) -> None:
        self._catalog = catalog

    def validate(
        self,
        version: WorkflowVersion,
        *,
        definition: WorkflowDefinition | None = None,
        policy: ValidationPolicyFacts | None = None,
    ) -> WorkflowValidationResult:
        if not isinstance(version, WorkflowVersion):
            raise TypeError("version must be a WorkflowVersion")
        if definition is not None and not isinstance(definition, WorkflowDefinition):
            raise TypeError("definition must be a WorkflowDefinition")
        facts = policy or ValidationPolicyFacts()
        issues: list[WorkflowValidationIssue] = []
        if definition is not None and definition.workflow_id != version.workflow_id:
            issues.append(validation_issue(ValidationIssueCode.WORKFLOW_REFERENCE_MISMATCH, ValidationSeverity.BLOCKING, ValidationLayer.SCHEMA))
        if not version.rules:
            issues.append(validation_issue(ValidationIssueCode.EMPTY_WORKFLOW, ValidationSeverity.BLOCKING, ValidationLayer.SCHEMA))
        rule_ids = [rule.rule_id for rule in version.rules]
        if len(set(rule_ids)) != len(rule_ids):
            issues.append(validation_issue(ValidationIssueCode.DUPLICATE_RULE_ID, ValidationSeverity.BLOCKING, ValidationLayer.SCHEMA))
        orders = [rule.order for rule in version.rules]
        if len(set(orders)) != len(orders):
            issues.append(validation_issue(ValidationIssueCode.DUPLICATE_RULE_ORDER, ValidationSeverity.ERROR, ValidationLayer.SEMANTIC))

        dependency_result = validate_dependencies(version.rules)
        issues.extend(dependency_result.issues)
        operation_results = []
        rule_results = []
        for rule in sorted(version.rules, key=lambda item: (item.order, item.rule_id)):
            structural_rule_issues = []
            if rule.enabled and rule.skip:
                structural_rule_issues.append(validation_issue(ValidationIssueCode.INVALID_RULE_STATE, ValidationSeverity.ERROR, ValidationLayer.SEMANTIC, rule_id=rule.rule_id))
            if rule.condition is not None:
                structural_rule_issues.extend(validate_condition(rule.condition, rule_id=rule.rule_id))
            for hint in rule.input_contract_hints + rule.output_contract_hints:
                structural_rule_issues.extend(validate_logical_path(hint, rule_id=rule.rule_id))
            action_results = tuple(
                validate_action_compatibility(rule.rule_id, action, self._catalog, available_features=facts.available_features)
                for action in rule.actions if action.enabled
            )
            operation_results.extend(action_results)
            rule_issues = list(structural_rule_issues)
            for result in action_results:
                rule_issues.extend(result.issues)
            rule_valid = not _has_error(structural_rule_issues) and all(result.structurally_valid for result in action_results)
            rule_preview = rule_valid and all(result.preview_eligible for result in action_results)
            rule_publication = rule_valid and all(result.publication_eligible for result in action_results)
            rule_results.append(RuleValidationResult(rule.rule_id, rule_valid, rule_preview, rule_publication, tuple(rule_issues)))
            issues.extend(rule_issues)

        if facts.require_test_evidence and not facts.test_evidence_passed:
            issues.append(validation_issue(ValidationIssueCode.TEST_EVIDENCE_REQUIRED, ValidationSeverity.BLOCKING, ValidationLayer.PUBLICATION))
        if facts.require_approval_evidence and not facts.approval_evidence_present:
            issues.append(validation_issue(ValidationIssueCode.APPROVAL_EVIDENCE_REQUIRED, ValidationSeverity.BLOCKING, ValidationLayer.PUBLICATION))
        if facts.legacy_manual_review_required:
            issues.append(validation_issue(ValidationIssueCode.LEGACY_MANUAL_REVIEW, ValidationSeverity.BLOCKING, ValidationLayer.LEGACY_COMPATIBILITY))

        structural_layers = {ValidationLayer.SCHEMA, ValidationLayer.SEMANTIC, ValidationLayer.DEPENDENCY, ValidationLayer.PATH, ValidationLayer.SECURITY}
        structurally_valid = dependency_result.valid and not any(issue.layer in structural_layers and issue.severity in (ValidationSeverity.ERROR, ValidationSeverity.BLOCKING) for issue in issues)
        preview_eligible = structurally_valid and bool(rule_results) and all(result.preview_eligible for result in rule_results)
        test_ready = preview_eligible
        publication_eligible = structurally_valid and bool(rule_results) and all(result.publication_eligible for result in rule_results) and not _has_error(issues)
        return WorkflowValidationResult(
            version.workflow_id, version.version_id, structurally_valid, preview_eligible, test_ready,
            publication_eligible, not publication_eligible, dependency_result.ordered_rule_ids,
            tuple(_stable_issues(issues)), tuple(rule_results), dependency_result, tuple(operation_results),
        )


def validate_condition(condition: object, *, rule_id: str | None = None, depth: int = 1) -> tuple[WorkflowValidationIssue, ...]:
    issues = []
    if depth > 5:
        return (validation_issue(ValidationIssueCode.CONDITION_DEPTH_EXCEEDED, ValidationSeverity.ERROR, ValidationLayer.SEMANTIC, rule_id=rule_id),)
    if isinstance(condition, ConditionDefinition):
        issues.extend(validate_logical_path(condition.field_path, rule_id=rule_id))
        valueless = {ConditionOperator.EXISTS, ConditionOperator.NOT_EXISTS, ConditionOperator.IS_NULL, ConditionOperator.IS_NOT_NULL}
        membership = {ConditionOperator.IN, ConditionOperator.NOT_IN}
        comparisons = {
            ConditionOperator.GREATER_THAN, ConditionOperator.GREATER_THAN_OR_EQUAL,
            ConditionOperator.LESS_THAN, ConditionOperator.LESS_THAN_OR_EQUAL,
        }
        invalid = False
        if condition.operator in valueless:
            invalid = condition.value is not None or condition.null_policy is not NullPolicy.REJECT
        elif condition.operator in membership:
            invalid = not isinstance(condition.value, tuple) or not condition.value or len(condition.value) > 100
        elif condition.operator is ConditionOperator.MATCHES_REGEX:
            invalid = not isinstance(condition.value, str) or not condition.value or len(condition.value) > 256
        elif condition.operator in comparisons:
            invalid = condition.value is None or isinstance(condition.value, (bool, tuple))
        elif isinstance(condition.value, tuple):
            invalid = True
        if invalid:
            issues.append(validation_issue(ValidationIssueCode.INVALID_CONDITION_VALUE, ValidationSeverity.ERROR, ValidationLayer.SEMANTIC, rule_id=rule_id))
        return tuple(issues)
    if isinstance(condition, ConditionGroup):
        if len(condition.conditions) > 32:
            issues.append(validation_issue(ValidationIssueCode.CONDITION_WIDTH_EXCEEDED, ValidationSeverity.ERROR, ValidationLayer.SEMANTIC, rule_id=rule_id))
        if not condition.conditions or (condition.operator is BooleanOperator.NOT and len(condition.conditions) != 1):
            issues.append(validation_issue(ValidationIssueCode.INVALID_CONDITION, ValidationSeverity.ERROR, ValidationLayer.SEMANTIC, rule_id=rule_id))
        for child in condition.conditions:
            issues.extend(validate_condition(child, rule_id=rule_id, depth=depth + 1))
        return tuple(issues)
    return (validation_issue(ValidationIssueCode.INVALID_CONDITION, ValidationSeverity.ERROR, ValidationLayer.SEMANTIC, rule_id=rule_id),)


def _has_error(issues: Iterable[WorkflowValidationIssue]) -> bool:
    return any(issue.severity in (ValidationSeverity.ERROR, ValidationSeverity.BLOCKING) for issue in issues)


def _stable_issues(issues: Iterable[WorkflowValidationIssue]) -> list[WorkflowValidationIssue]:
    return sorted(issues, key=lambda item: (item.layer.value, item.rule_id or "", item.action_id or "", item.code))
