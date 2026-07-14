"""Stable validation issue codes and non-reflective summaries."""

from __future__ import annotations

from enum import Enum

from .validation_results import ValidationLayer, ValidationSeverity, WorkflowValidationIssue


class ValidationIssueCode(str, Enum):
    EMPTY_WORKFLOW = "empty_workflow"
    WORKFLOW_REFERENCE_MISMATCH = "workflow_reference_mismatch"
    DUPLICATE_RULE_ID = "duplicate_rule_id"
    DUPLICATE_RULE_ORDER = "duplicate_rule_order"
    INVALID_RULE_STATE = "invalid_rule_state"
    MISSING_DEPENDENCY = "missing_dependency"
    SELF_DEPENDENCY = "self_dependency"
    DUPLICATE_DEPENDENCY = "duplicate_dependency"
    DEPENDENCY_CYCLE = "dependency_cycle"
    INVALID_CONDITION = "invalid_condition"
    INVALID_CONDITION_VALUE = "invalid_condition_value"
    CONDITION_DEPTH_EXCEEDED = "condition_depth_exceeded"
    CONDITION_WIDTH_EXCEEDED = "condition_width_exceeded"
    INVALID_PATH = "invalid_path"
    PROTECTED_PATH = "protected_path"
    OPERATION_NOT_FOUND = "operation_not_found"
    OPERATION_VERSION_NOT_FOUND = "operation_version_not_found"
    OPERATION_UNAVAILABLE = "operation_unavailable"
    OPERATION_PREVIEW_BLOCKED = "operation_preview_blocked"
    OPERATION_PUBLICATION_BLOCKED = "operation_publication_blocked"
    MISSING_ARGUMENT = "missing_argument"
    UNKNOWN_ARGUMENT = "unknown_argument"
    INVALID_ARGUMENT_TYPE = "invalid_argument_type"
    SOURCE_PATH_REQUIRED = "source_path_required"
    TARGET_PATH_REQUIRED = "target_path_required"
    RUNTIME_MAPPING_UNPROVEN = "runtime_mapping_unproven"
    REQUIRED_FEATURE_UNAVAILABLE = "required_feature_unavailable"
    TEST_EVIDENCE_REQUIRED = "test_evidence_required"
    APPROVAL_EVIDENCE_REQUIRED = "approval_evidence_required"
    LEGACY_MANUAL_REVIEW = "legacy_manual_review"
    LEGACY_PARTIAL_SUPPORT = "legacy_partial_support"
    LEGACY_UNSUPPORTED = "legacy_unsupported"


_SUMMARIES = {
    ValidationIssueCode.EMPTY_WORKFLOW: "Workflow version must contain at least one rule.",
    ValidationIssueCode.WORKFLOW_REFERENCE_MISMATCH: "Workflow definition and version identifiers do not match.",
    ValidationIssueCode.DUPLICATE_RULE_ID: "Workflow rule identifiers must be unique.",
    ValidationIssueCode.DUPLICATE_RULE_ORDER: "Workflow rule order values must be unique.",
    ValidationIssueCode.INVALID_RULE_STATE: "Workflow rule enabled and skip state is inconsistent.",
    ValidationIssueCode.MISSING_DEPENDENCY: "A rule dependency does not exist in this workflow version.",
    ValidationIssueCode.SELF_DEPENDENCY: "A rule cannot depend on itself.",
    ValidationIssueCode.DUPLICATE_DEPENDENCY: "Rule dependencies must not contain duplicates.",
    ValidationIssueCode.DEPENDENCY_CYCLE: "Workflow rule dependencies contain a cycle.",
    ValidationIssueCode.INVALID_CONDITION: "Condition structure or operator policy is invalid.",
    ValidationIssueCode.INVALID_CONDITION_VALUE: "Condition value is incompatible with its operator.",
    ValidationIssueCode.CONDITION_DEPTH_EXCEEDED: "Condition nesting exceeds the supported depth.",
    ValidationIssueCode.CONDITION_WIDTH_EXCEEDED: "Condition group exceeds the supported width.",
    ValidationIssueCode.INVALID_PATH: "Logical field path is invalid.",
    ValidationIssueCode.PROTECTED_PATH: "Logical field path targets a protected platform namespace.",
    ValidationIssueCode.OPERATION_NOT_FOUND: "Action operation is not present in the Studio catalog.",
    ValidationIssueCode.OPERATION_VERSION_NOT_FOUND: "Requested action operation version is not present in the Studio catalog.",
    ValidationIssueCode.OPERATION_UNAVAILABLE: "Action operation is currently unavailable.",
    ValidationIssueCode.OPERATION_PREVIEW_BLOCKED: "Action operation is not eligible for preview.",
    ValidationIssueCode.OPERATION_PUBLICATION_BLOCKED: "Action operation is not eligible for publication.",
    ValidationIssueCode.MISSING_ARGUMENT: "Action is missing a required operation argument.",
    ValidationIssueCode.UNKNOWN_ARGUMENT: "Action contains an argument not declared by the operation.",
    ValidationIssueCode.INVALID_ARGUMENT_TYPE: "Action argument type is incompatible with the operation contract.",
    ValidationIssueCode.SOURCE_PATH_REQUIRED: "Action operation requires a source path.",
    ValidationIssueCode.TARGET_PATH_REQUIRED: "Action operation requires a target path.",
    ValidationIssueCode.RUNTIME_MAPPING_UNPROVEN: "Action operation does not have a proven runtime mapping.",
    ValidationIssueCode.REQUIRED_FEATURE_UNAVAILABLE: "An operation-required feature is unavailable.",
    ValidationIssueCode.TEST_EVIDENCE_REQUIRED: "Publication policy requires passing test evidence.",
    ValidationIssueCode.APPROVAL_EVIDENCE_REQUIRED: "Publication policy requires approval evidence.",
    ValidationIssueCode.LEGACY_MANUAL_REVIEW: "Legacy operation requires explicit manual review.",
    ValidationIssueCode.LEGACY_PARTIAL_SUPPORT: "Legacy operation has only a partial Studio mapping.",
    ValidationIssueCode.LEGACY_UNSUPPORTED: "Legacy operation is unsupported by the current Studio boundary.",
}


def validation_issue(
    code: ValidationIssueCode,
    severity: ValidationSeverity,
    layer: ValidationLayer,
    *,
    rule_id: str | None = None,
    action_id: str | None = None,
    path: str | None = None,
) -> WorkflowValidationIssue:
    return WorkflowValidationIssue(code.value, severity, layer, _SUMMARIES[code], rule_id, action_id, path)
