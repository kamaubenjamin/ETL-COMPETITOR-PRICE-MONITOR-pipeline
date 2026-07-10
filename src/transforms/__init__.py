"""Reusable transformation pipeline primitives."""

from src.transforms.contracts import (
    AggregationDefinition,
    AggregationPlan,
    DataValidationResult,
    FieldMapping,
    OperationDefinition,
    RegexDefinition,
    SortKey,
    SortPlan,
    TransformationPlan,
    ValidationIssue,
    ValidationPlan,
    ValidationResult,
    ValidationRule,
)
from src.transforms.errors import ConfigurationError
from src.transforms.executor import TransformationExecutor
from src.transforms.field_mapping import apply_field_mappings, coerce_series
from src.transforms.pipeline import TransformationPipeline
from src.transforms.regex_registry import RegexRegistry
from src.transforms.registry import DEFAULT_OPERATION_REGISTRY, OperationRegistry

__all__ = [
    "AggregationDefinition",
    "AggregationPlan",
    "ConfigurationError",
    "DataValidationResult",
    "DEFAULT_OPERATION_REGISTRY",
    "FieldMapping",
    "OperationDefinition",
    "OperationRegistry",
    "RegexDefinition",
    "RegexRegistry",
    "SortKey",
    "SortPlan",
    "TransformationPipeline",
    "TransformationExecutor",
    "TransformationPlan",
    "ValidationIssue",
    "ValidationPlan",
    "ValidationResult",
    "ValidationRule",
    "apply_field_mappings",
    "coerce_series",
]
