"""Pure action-to-operation compatibility validation."""

from __future__ import annotations

from collections.abc import Iterable

from .actions import ActionDefinition
from .operation_catalog import (
    InMemoryWorkflowOperationCatalog,
    OperationArgumentType,
    OperationDeterminism,
)
from .path_validation import validate_logical_path
from .ports import WorkflowOperationCatalogPort
from .statuses import OperationAvailabilityStatus
from .validation_errors import ValidationIssueCode, validation_issue
from .validation_results import (
    OperationCompatibilityResult,
    ValidationLayer,
    ValidationSeverity,
)


def validate_action_compatibility(
    rule_id: str,
    action: ActionDefinition,
    catalog: WorkflowOperationCatalogPort | None = None,
    *,
    available_features: Iterable[str] = (),
) -> OperationCompatibilityResult:
    operation_catalog = catalog or InMemoryWorkflowOperationCatalog()
    features = frozenset(available_features)
    issues = []
    by_name = operation_catalog.get_operation(action.operation_name)
    operation = operation_catalog.get_operation(action.operation_name, action.operation_version)
    if by_name is None:
        issues.append(_issue(ValidationIssueCode.OPERATION_NOT_FOUND, rule_id, action.action_id, ValidationSeverity.BLOCKING))
    elif operation is None:
        issues.append(_issue(ValidationIssueCode.OPERATION_VERSION_NOT_FOUND, rule_id, action.action_id, ValidationSeverity.BLOCKING))
    if operation is None:
        return OperationCompatibilityResult(
            rule_id, action.action_id, action.operation_name, action.operation_version,
            False, False, False, (), (), None, tuple(issues),
        )

    if operation.availability is not OperationAvailabilityStatus.AVAILABLE:
        issues.append(_issue(ValidationIssueCode.OPERATION_UNAVAILABLE, rule_id, action.action_id, ValidationSeverity.BLOCKING))
    declared = {argument.name: argument for argument in operation.arguments}
    supplied = set(action.arguments)
    for name in sorted(name for name, argument in declared.items() if argument.required and name not in supplied):
        issues.append(_issue(ValidationIssueCode.MISSING_ARGUMENT, rule_id, action.action_id, ValidationSeverity.ERROR))
    for name in sorted(supplied - set(declared)):
        issues.append(_issue(ValidationIssueCode.UNKNOWN_ARGUMENT, rule_id, action.action_id, ValidationSeverity.ERROR))
    for name in sorted(supplied.intersection(declared)):
        if not _argument_matches(action.arguments[name], declared[name].value_type):
            issues.append(_issue(ValidationIssueCode.INVALID_ARGUMENT_TYPE, rule_id, action.action_id, ValidationSeverity.ERROR))

    if operation.requires_source_path and action.source_path is None:
        issues.append(_issue(ValidationIssueCode.SOURCE_PATH_REQUIRED, rule_id, action.action_id, ValidationSeverity.ERROR))
    if operation.requires_target_path and action.target_path is None:
        issues.append(_issue(ValidationIssueCode.TARGET_PATH_REQUIRED, rule_id, action.action_id, ValidationSeverity.ERROR))
    if action.source_path is not None:
        issues.extend(validate_logical_path(action.source_path, rule_id=rule_id, action_id=action.action_id))
    if action.target_path is not None:
        issues.extend(validate_logical_path(action.target_path, rule_id=rule_id, action_id=action.action_id))

    missing_features = tuple(sorted(set(operation.required_features) - features))
    if missing_features:
        issues.append(_issue(ValidationIssueCode.REQUIRED_FEATURE_UNAVAILABLE, rule_id, action.action_id, ValidationSeverity.BLOCKING))
    if not operation.preview_eligible:
        issues.append(_issue(ValidationIssueCode.OPERATION_PREVIEW_BLOCKED, rule_id, action.action_id, ValidationSeverity.WARNING))
    if not operation.publication_eligible:
        issues.append(_issue(ValidationIssueCode.OPERATION_PUBLICATION_BLOCKED, rule_id, action.action_id, ValidationSeverity.BLOCKING))
    if not operation.runtime_mapping_proven or operation.runtime_operation is None:
        issues.append(_issue(ValidationIssueCode.RUNTIME_MAPPING_UNPROVEN, rule_id, action.action_id, ValidationSeverity.BLOCKING))

    structural_codes = {
        ValidationIssueCode.MISSING_ARGUMENT.value,
        ValidationIssueCode.UNKNOWN_ARGUMENT.value,
        ValidationIssueCode.INVALID_ARGUMENT_TYPE.value,
        ValidationIssueCode.SOURCE_PATH_REQUIRED.value,
        ValidationIssueCode.TARGET_PATH_REQUIRED.value,
        ValidationIssueCode.INVALID_PATH.value,
        ValidationIssueCode.PROTECTED_PATH.value,
    }
    structurally_valid = not any(issue.code in structural_codes for issue in issues)
    preview_eligible = structurally_valid and operation.preview_eligible and not missing_features and operation.determinism is OperationDeterminism.DETERMINISTIC
    publication_eligible = structurally_valid and operation.publication_eligible and not missing_features and operation.runtime_mapping_proven
    return OperationCompatibilityResult(
        rule_id, action.action_id, operation.name, operation.version, structurally_valid,
        preview_eligible, publication_eligible, operation.required_features, missing_features,
        operation.runtime_operation if operation.runtime_mapping_proven else None, tuple(issues),
    )


def _argument_matches(value: object, expected: OperationArgumentType) -> bool:
    if expected is OperationArgumentType.STRING:
        return isinstance(value, str)
    if expected is OperationArgumentType.INTEGER:
        return isinstance(value, int) and not isinstance(value, bool)
    if expected is OperationArgumentType.NUMBER:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected is OperationArgumentType.BOOLEAN:
        return isinstance(value, bool)
    if expected is OperationArgumentType.SCALAR_LIST:
        return isinstance(value, tuple)
    return not isinstance(value, tuple)


def _issue(code: ValidationIssueCode, rule_id: str, action_id: str, severity: ValidationSeverity):
    return validation_issue(code, severity, ValidationLayer.OPERATION_COMPATIBILITY, rule_id=rule_id, action_id=action_id)
