"""Governed, non-executable Workflow Studio foundation contracts."""

from .actions import ActionDefinition, ActionErrorPolicy, ActionOutputPolicy
from .conditions import BooleanOperator, ConditionDefinition, ConditionGroup, ConditionOperator, NullPolicy
from .compatibility import validate_action_compatibility
from .definitions import (
    RuleDefinition,
    WorkflowChangeSummary,
    WorkflowDefinition,
    WorkflowOwnership,
    WorkflowPublication,
    WorkflowReference,
    WorkflowSourceLineage,
    WorkflowVersion,
)
from .errors import WorkflowStudioError, WorkflowStudioErrorCode
from .dependencies import RuleDependencyNode, validate_dependencies
from .legacy import (
    LegacyActionDescriptor,
    LegacyCompatibilityReport,
    LegacyOperationCompatibility,
    LegacyRuleDescriptor,
    LegacyWorkflowDescriptor,
    generate_legacy_compatibility_report,
)
from .operation_catalog import (
    DEFAULT_OPERATIONS,
    InMemoryWorkflowOperationCatalog,
    OperationArgumentDefinition,
    OperationArgumentType,
    OperationCategory,
    OperationContractHint,
    OperationDeterminism,
    OperationExecutionMode,
    StudioOperationDefinition,
)
from .ports import (
    WorkflowDefinitionReadPort,
    WorkflowDefinitionWritePort,
    WorkflowOperationCatalogPort,
    WorkflowVersionReadPort,
    WorkflowVersionWritePort,
)
from .path_validation import PROTECTED_PATH_PREFIXES, safe_logical_path, validate_logical_path
from .statuses import (
    OperationAvailabilityStatus,
    RuleStatus,
    WorkflowDefinitionStatus,
    WorkflowPublicationStatus,
    WorkflowVersionStatus,
)
from .validation import ValidationPolicyFacts, WorkflowValidationService, validate_condition
from .validation_errors import ValidationIssueCode
from .validation_results import (
    DependencyValidationResult,
    LegacyCompatibilityStatus,
    OperationCompatibilityResult,
    RuleValidationResult,
    ValidationLayer,
    ValidationSeverity,
    WorkflowValidationIssue,
    WorkflowValidationResult,
)

__all__ = [
    "ActionDefinition", "ActionErrorPolicy", "ActionOutputPolicy", "BooleanOperator",
    "ConditionDefinition", "ConditionGroup", "ConditionOperator", "DEFAULT_OPERATIONS",
    "DependencyValidationResult", "InMemoryWorkflowOperationCatalog", "LegacyActionDescriptor",
    "LegacyCompatibilityReport", "LegacyCompatibilityStatus", "LegacyOperationCompatibility",
    "LegacyRuleDescriptor", "LegacyWorkflowDescriptor", "NullPolicy", "OperationArgumentDefinition",
    "OperationArgumentType", "OperationAvailabilityStatus", "OperationCategory",
    "OperationCompatibilityResult", "OperationContractHint", "OperationDeterminism",
    "OperationExecutionMode", "PROTECTED_PATH_PREFIXES", "RuleDefinition", "RuleDependencyNode",
    "RuleValidationResult",
    "RuleStatus", "StudioOperationDefinition", "WorkflowChangeSummary", "WorkflowDefinition",
    "WorkflowDefinitionReadPort", "WorkflowDefinitionStatus", "WorkflowDefinitionWritePort",
    "WorkflowOperationCatalogPort", "WorkflowOwnership", "WorkflowPublication",
    "WorkflowPublicationStatus", "WorkflowReference", "WorkflowSourceLineage", "WorkflowStudioError",
    "WorkflowStudioErrorCode", "WorkflowValidationIssue", "WorkflowValidationResult",
    "WorkflowValidationService", "WorkflowVersion", "WorkflowVersionReadPort", "WorkflowVersionStatus",
    "WorkflowVersionWritePort", "ValidationIssueCode", "ValidationLayer", "ValidationPolicyFacts",
    "ValidationSeverity", "generate_legacy_compatibility_report", "safe_logical_path",
    "validate_action_compatibility", "validate_condition", "validate_dependencies", "validate_logical_path",
]
