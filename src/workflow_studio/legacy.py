"""Non-executable legacy Sanifu/Docsift compatibility reporting."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from .contracts import (
    SafeArgumentValue,
    StudioContract,
    bounded_text,
    safe_arguments,
    safe_code,
    safe_metadata,
    stable_id,
)
from .operation_catalog import InMemoryWorkflowOperationCatalog
from .ports import WorkflowOperationCatalogPort
from .statuses import OperationAvailabilityStatus
from .validation_results import LegacyCompatibilityStatus


@dataclass(frozen=True, slots=True)
class LegacyActionDescriptor(StudioContract):
    action_id: str
    label: str
    arguments: Mapping[str, SafeArgumentValue] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "action_id", stable_id(self.action_id, "action_id"))
        object.__setattr__(self, "label", safe_code(self.label, "legacy action label"))
        object.__setattr__(self, "arguments", safe_arguments(self.arguments))


@dataclass(frozen=True, slots=True)
class LegacyRuleDescriptor(StudioContract):
    rule_id: str
    stage: str
    description: str
    dependencies: tuple[str, ...]
    skip: bool
    condition: str | None
    actions: tuple[LegacyActionDescriptor, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", stable_id(self.rule_id, "rule_id"))
        object.__setattr__(self, "stage", stable_id(self.stage, "stage"))
        object.__setattr__(self, "description", bounded_text(self.description, "description", maximum=1024, allow_empty=True))
        if not isinstance(self.dependencies, (tuple, list)) or len(self.dependencies) > 32:
            raise ValueError("legacy dependencies must be bounded")
        object.__setattr__(self, "dependencies", tuple(stable_id(item, "dependency") for item in self.dependencies))
        if not isinstance(self.skip, bool):
            raise ValueError("legacy skip must be a boolean")
        object.__setattr__(self, "condition", None if self.condition is None else safe_code(self.condition, "legacy condition"))
        if not isinstance(self.actions, (tuple, list)) or len(self.actions) > 32 or not all(isinstance(item, LegacyActionDescriptor) for item in self.actions):
            raise ValueError("legacy actions must be a bounded modeled sequence")
        object.__setattr__(self, "actions", tuple(self.actions))


@dataclass(frozen=True, slots=True)
class LegacyWorkflowDescriptor(StudioContract):
    source_system: str
    source_reference: str
    workflow_label: str
    rules: tuple[LegacyRuleDescriptor, ...]
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_system", stable_id(self.source_system, "source_system"))
        object.__setattr__(self, "source_reference", stable_id(self.source_reference, "source_reference"))
        object.__setattr__(self, "workflow_label", stable_id(self.workflow_label, "workflow_label"))
        if not isinstance(self.rules, (tuple, list)) or len(self.rules) > 100 or not all(isinstance(item, LegacyRuleDescriptor) for item in self.rules):
            raise ValueError("legacy rules must be a bounded modeled sequence")
        object.__setattr__(self, "rules", tuple(self.rules))
        object.__setattr__(self, "metadata", safe_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class LegacyOperationCompatibility(StudioContract):
    rule_id: str
    action_id: str
    legacy_label: str
    status: LegacyCompatibilityStatus
    reason_code: str
    summary: str
    candidate_operation: str | None
    missing_runtime_or_compiler_proof: bool
    required_features: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", stable_id(self.rule_id, "rule_id"))
        object.__setattr__(self, "action_id", stable_id(self.action_id, "action_id"))
        object.__setattr__(self, "legacy_label", safe_code(self.legacy_label, "legacy_label"))
        try:
            status = self.status if isinstance(self.status, LegacyCompatibilityStatus) else LegacyCompatibilityStatus(self.status)
        except (TypeError, ValueError) as error:
            raise ValueError("legacy compatibility status is unsupported") from error
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "reason_code", safe_code(self.reason_code, "reason_code"))
        object.__setattr__(self, "summary", bounded_text(self.summary, "summary", maximum=256))
        object.__setattr__(self, "candidate_operation", None if self.candidate_operation is None else safe_code(self.candidate_operation, "candidate_operation"))
        if not isinstance(self.missing_runtime_or_compiler_proof, bool):
            raise ValueError("missing proof indicator must be a boolean")
        if not isinstance(self.required_features, (tuple, list)) or len(self.required_features) > 16:
            raise ValueError("required_features must be bounded")
        object.__setattr__(self, "required_features", tuple(safe_code(item, "required_feature") for item in self.required_features))


@dataclass(frozen=True, slots=True)
class LegacyCompatibilityReport(StudioContract):
    source_system: str
    source_reference: str
    workflow_label: str
    overall_status: LegacyCompatibilityStatus
    operations: tuple[LegacyOperationCompatibility, ...]
    manual_review_required: bool
    executable_conversion_produced: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_system", stable_id(self.source_system, "source_system"))
        object.__setattr__(self, "source_reference", stable_id(self.source_reference, "source_reference"))
        object.__setattr__(self, "workflow_label", stable_id(self.workflow_label, "workflow_label"))
        try:
            status = self.overall_status if isinstance(self.overall_status, LegacyCompatibilityStatus) else LegacyCompatibilityStatus(self.overall_status)
        except (TypeError, ValueError) as error:
            raise ValueError("overall_status is unsupported") from error
        object.__setattr__(self, "overall_status", status)
        if not isinstance(self.operations, (tuple, list)) or len(self.operations) > 3200 or not all(isinstance(item, LegacyOperationCompatibility) for item in self.operations):
            raise ValueError("operations must be a bounded modeled sequence")
        object.__setattr__(self, "operations", tuple(self.operations))
        if not isinstance(self.manual_review_required, bool) or self.executable_conversion_produced is not False:
            raise ValueError("legacy reports are non-executable and require boolean review state")


_PARTIAL_MAPPINGS = MappingProxyType({
    "set": "set", "remove_path": "remove_path", "concat": "concat", "map": None,
    "regex_mapper": "regex_mapper", "regex_extract": "regex_extract",
    "convert_units_v2": "convert_units", "append": "append", "strtoupper": "uppercase",
    "make_object_list_unique": "unique", "window_conditional_filter": "conditional_filter",
    "date_format": "date_format", "split": "split", "remove_repeated_words": "normalize",
})
_MANUAL = frozenset({"function", "transform"})
_UNSUPPORTED_FEATURES = MappingProxyType({
    "map_parallel": ("parallel_map_runtime",),
    "fuzzy_extract_n": ("fuzzy_extract_runtime",),
    "fuzzy_search": ("search_port",),
    "historical_search": ("historical_search_port",),
    "get_master_data": ("master_data_port",),
    "semantic_search": ("semantic_search_port",),
    "semantic_classification": ("semantic_classification_port",),
    "parse_template": ("template_parser",),
    "reducer": ("bounded_reducer_compiler",),
    "concat_multi_array_assoc": ("complex_collection_compiler",),
})
_SUMMARIES = {
    LegacyCompatibilityStatus.SUPPORTED: "Legacy operation has an exact proven Studio operation mapping.",
    LegacyCompatibilityStatus.PARTIALLY_SUPPORTED: "Legacy concept is recognized but exact semantics are not proven.",
    LegacyCompatibilityStatus.UNSUPPORTED: "Legacy operation requires an unavailable or unapproved capability.",
    LegacyCompatibilityStatus.MANUAL_REVIEW_REQUIRED: "Legacy wrapper semantics require explicit human review.",
}


def generate_legacy_compatibility_report(
    descriptor: LegacyWorkflowDescriptor,
    catalog: WorkflowOperationCatalogPort | None = None,
) -> LegacyCompatibilityReport:
    if not isinstance(descriptor, LegacyWorkflowDescriptor):
        raise TypeError("descriptor must be a LegacyWorkflowDescriptor")
    operation_catalog = catalog or InMemoryWorkflowOperationCatalog()
    results = []
    for rule in descriptor.rules:
        for action in rule.actions:
            results.append(_classify(rule.rule_id, action, operation_catalog))
    statuses = {item.status for item in results}
    if LegacyCompatibilityStatus.UNSUPPORTED in statuses:
        overall = LegacyCompatibilityStatus.UNSUPPORTED
    elif LegacyCompatibilityStatus.MANUAL_REVIEW_REQUIRED in statuses:
        overall = LegacyCompatibilityStatus.MANUAL_REVIEW_REQUIRED
    elif LegacyCompatibilityStatus.PARTIALLY_SUPPORTED in statuses:
        overall = LegacyCompatibilityStatus.PARTIALLY_SUPPORTED
    else:
        overall = LegacyCompatibilityStatus.SUPPORTED
    manual = any(item.status is not LegacyCompatibilityStatus.SUPPORTED for item in results)
    return LegacyCompatibilityReport(
        descriptor.source_system, descriptor.source_reference, descriptor.workflow_label,
        overall, tuple(results), manual, False,
    )


def _classify(rule_id: str, action: LegacyActionDescriptor, catalog: WorkflowOperationCatalogPort) -> LegacyOperationCompatibility:
    exact = catalog.get_operation(action.label)
    if exact is not None and exact.availability is OperationAvailabilityStatus.AVAILABLE and exact.runtime_mapping_proven:
        status = LegacyCompatibilityStatus.SUPPORTED
        candidate = exact.name
        reason = "exact_mapping_proven"
        features = exact.required_features
        missing_proof = False
    elif action.label in _PARTIAL_MAPPINGS:
        status = LegacyCompatibilityStatus.PARTIALLY_SUPPORTED
        candidate = _PARTIAL_MAPPINGS[action.label]
        reason = "semantic_equivalence_unproven"
        mapped = None if candidate is None else catalog.get_operation(candidate)
        features = ("workflow_operation_compiler",) if mapped is None else mapped.required_features
        missing_proof = True
    elif action.label in _MANUAL:
        status = LegacyCompatibilityStatus.MANUAL_REVIEW_REQUIRED
        candidate = None
        reason = "generic_wrapper_requires_review"
        features = ()
        missing_proof = True
    else:
        status = LegacyCompatibilityStatus.UNSUPPORTED
        candidate = None
        reason = "capability_unavailable"
        features = _UNSUPPORTED_FEATURES.get(action.label, ())
        missing_proof = True
    return LegacyOperationCompatibility(
        rule_id, action.action_id, action.label, status, reason, _SUMMARIES[status],
        candidate, missing_proof, features,
    )
