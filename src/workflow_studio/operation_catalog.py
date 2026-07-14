"""Conservative business-safe operation catalog for Workflow Studio."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

from .contracts import (
    SafeArgumentValue,
    StudioContract,
    bounded_text,
    logical_path,
    safe_code,
    safe_scalar,
    stable_id,
    version_label,
)
from .statuses import OperationAvailabilityStatus


class OperationCategory(str, Enum):
    ASSIGNMENT = "assignment"
    TRANSFORMATION = "transformation"
    FILTERING = "filtering"
    VALIDATION = "validation"
    MATCHING = "matching"
    AGGREGATION = "aggregation"
    UNITS = "units"


class OperationDeterminism(str, Enum):
    DETERMINISTIC = "deterministic"
    NON_DETERMINISTIC = "non_deterministic"


class OperationExecutionMode(str, Enum):
    RUNTIME = "runtime"
    COMPILER = "compiler"
    UNAVAILABLE = "unavailable"


class OperationArgumentType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SCALAR = "scalar"
    SCALAR_LIST = "scalar_list"


@dataclass(frozen=True, slots=True)
class OperationArgumentDefinition(StudioContract):
    name: str
    value_type: OperationArgumentType
    required: bool = False
    default: SafeArgumentValue = None
    description: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", safe_code(self.name, "argument name"))
        try:
            value_type = self.value_type if isinstance(self.value_type, OperationArgumentType) else OperationArgumentType(self.value_type)
        except (TypeError, ValueError) as error:
            raise ValueError("argument value_type is unsupported") from error
        if not isinstance(self.required, bool):
            raise ValueError("argument required must be a boolean")
        if isinstance(self.default, (tuple, list)):
            if len(self.default) > 100:
                raise ValueError("argument default list is too large")
            default = tuple(safe_scalar(item, "argument default", reject_code_like=True) for item in self.default)
        else:
            default = safe_scalar(self.default, "argument default", reject_code_like=True)
        object.__setattr__(self, "value_type", value_type)
        object.__setattr__(self, "default", default)
        object.__setattr__(self, "description", bounded_text(self.description, "argument description", maximum=256, allow_empty=True))


@dataclass(frozen=True, slots=True)
class OperationContractHint(StudioContract):
    label: str
    fields: tuple[str, ...] = ()
    collection: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "label", stable_id(self.label, "contract hint label"))
        if not isinstance(self.fields, (tuple, list)) or len(self.fields) > 32:
            raise ValueError("contract hint fields must be bounded")
        fields = tuple(logical_path(item, "contract hint field") for item in self.fields)
        if len(set(fields)) != len(fields):
            raise ValueError("contract hint fields must not contain duplicates")
        if not isinstance(self.collection, bool):
            raise ValueError("contract hint collection must be a boolean")
        object.__setattr__(self, "fields", fields)


@dataclass(frozen=True, slots=True)
class StudioOperationDefinition(StudioContract):
    name: str
    version: str
    category: OperationCategory
    description: str
    availability: OperationAvailabilityStatus
    determinism: OperationDeterminism
    execution_mode: OperationExecutionMode
    runtime_operation: str | None
    runtime_mapping_proven: bool
    preview_eligible: bool
    publication_eligible: bool
    required_features: tuple[str, ...] = ()
    arguments: tuple[OperationArgumentDefinition, ...] = ()
    input_contract_hints: tuple[OperationContractHint, ...] = ()
    output_contract_hints: tuple[OperationContractHint, ...] = ()
    privacy_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", safe_code(self.name, "operation name"))
        object.__setattr__(self, "version", version_label(self.version, "operation version"))
        for field_name, enum_type in (
            ("category", OperationCategory),
            ("availability", OperationAvailabilityStatus),
            ("determinism", OperationDeterminism),
            ("execution_mode", OperationExecutionMode),
        ):
            value = getattr(self, field_name)
            try:
                object.__setattr__(self, field_name, value if isinstance(value, enum_type) else enum_type(value))
            except (TypeError, ValueError) as error:
                raise ValueError(f"{field_name} is unsupported") from error
        object.__setattr__(self, "description", bounded_text(self.description, "description", maximum=512))
        if self.runtime_operation is not None:
            object.__setattr__(self, "runtime_operation", safe_code(self.runtime_operation, "runtime_operation"))
        for field_name in ("runtime_mapping_proven", "preview_eligible", "publication_eligible"):
            if not isinstance(getattr(self, field_name), bool):
                raise ValueError(f"{field_name} must be a boolean")
        object.__setattr__(self, "required_features", _labels(self.required_features, "required_features"))
        object.__setattr__(self, "arguments", _modeled(self.arguments, OperationArgumentDefinition, "arguments"))
        object.__setattr__(self, "input_contract_hints", _modeled(self.input_contract_hints, OperationContractHint, "input_contract_hints"))
        object.__setattr__(self, "output_contract_hints", _modeled(self.output_contract_hints, OperationContractHint, "output_contract_hints"))
        object.__setattr__(self, "privacy_notes", _notes(self.privacy_notes))
        if self.availability is not OperationAvailabilityStatus.AVAILABLE and (self.preview_eligible or self.publication_eligible):
            raise ValueError("unavailable operations cannot be preview or publication eligible")
        if self.preview_eligible and self.determinism is not OperationDeterminism.DETERMINISTIC:
            raise ValueError("only deterministic operations may be preview eligible")
        if self.publication_eligible and not (
            self.availability is OperationAvailabilityStatus.AVAILABLE
            and self.determinism is OperationDeterminism.DETERMINISTIC
            and self.runtime_mapping_proven
            and self.runtime_operation is not None
        ):
            raise ValueError("publication eligibility requires a proven deterministic runtime mapping")
        if self.runtime_mapping_proven and self.runtime_operation is None:
            raise ValueError("a proven runtime mapping requires a runtime operation label")


class InMemoryWorkflowOperationCatalog:
    """Read-only deterministic catalog; it is not a workflow repository."""

    def __init__(self, operations: Iterable[StudioOperationDefinition] | None = None) -> None:
        entries = tuple(operations) if operations is not None else DEFAULT_OPERATIONS
        ordered = tuple(sorted(entries, key=lambda item: (item.name, item.version)))
        if not all(isinstance(item, StudioOperationDefinition) for item in ordered):
            raise ValueError("catalog entries must be StudioOperationDefinition values")
        keys = tuple((item.name, item.version) for item in ordered)
        if len(set(keys)) != len(keys):
            raise ValueError("catalog operation name/version pairs must be unique")
        self._operations = ordered
        self._by_key: Mapping[tuple[str, str], StudioOperationDefinition] = MappingProxyType(dict(zip(keys, ordered)))

    def get_operation(self, name: str, version: str | None = None) -> StudioOperationDefinition | None:
        safe_name = safe_code(name, "operation name")
        if version is not None:
            return self._by_key.get((safe_name, version_label(version, "operation version")))
        matches = [item for item in self._operations if item.name == safe_name]
        return matches[-1] if matches else None

    def list_operations(
        self,
        *,
        category: OperationCategory | None = None,
        availability: OperationAvailabilityStatus | None = None,
    ) -> tuple[StudioOperationDefinition, ...]:
        normalized_category = None if category is None else (category if isinstance(category, OperationCategory) else OperationCategory(category))
        normalized_availability = None if availability is None else (
            availability if isinstance(availability, OperationAvailabilityStatus) else OperationAvailabilityStatus(availability)
        )
        return tuple(
            item for item in self._operations
            if (normalized_category is None or item.category is normalized_category)
            and (normalized_availability is None or item.availability is normalized_availability)
        )


def _modeled(values: Any, expected: type, field_name: str) -> tuple[Any, ...]:
    if not isinstance(values, (tuple, list)) or len(values) > 32 or not all(isinstance(item, expected) for item in values):
        raise ValueError(f"{field_name} must be a bounded modeled sequence")
    return tuple(values)


def _labels(values: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)) or len(values) > 32:
        raise ValueError(f"{field_name} must be a bounded label sequence")
    result = tuple(safe_code(item, field_name) for item in values)
    if len(set(result)) != len(result):
        raise ValueError(f"{field_name} must not contain duplicates")
    return result


def _notes(values: Any) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)) or len(values) > 16:
        raise ValueError("privacy_notes must be bounded")
    return tuple(bounded_text(item, "privacy note", maximum=256) for item in values)


def _operation(name: str, category: OperationCategory, *, proven: bool = False, mapping: str = "transform") -> StudioOperationDefinition:
    available = OperationAvailabilityStatus.AVAILABLE if proven else OperationAvailabilityStatus.UNAVAILABLE
    return StudioOperationDefinition(
        name=name,
        version="1",
        category=category,
        description=f"Governed {name.replace('_', ' ')} operation contract.",
        availability=available,
        determinism=OperationDeterminism.DETERMINISTIC,
        execution_mode=OperationExecutionMode.RUNTIME if proven else OperationExecutionMode.UNAVAILABLE,
        runtime_operation=mapping,
        runtime_mapping_proven=proven,
        preview_eligible=proven,
        publication_eligible=proven,
        required_features=() if proven else ("workflow_operation_compiler",),
        privacy_notes=("Accepts modeled fields and bounded scalar configuration only.",),
    )


_SPECS = (
    ("set", OperationCategory.ASSIGNMENT),
    ("remove_path", OperationCategory.ASSIGNMENT),
    ("append", OperationCategory.ASSIGNMENT),
    ("trim", OperationCategory.TRANSFORMATION),
    ("normalize", OperationCategory.TRANSFORMATION),
    ("uppercase", OperationCategory.TRANSFORMATION),
    ("lowercase", OperationCategory.TRANSFORMATION),
    ("concat", OperationCategory.TRANSFORMATION),
    ("split", OperationCategory.TRANSFORMATION),
    ("date_format", OperationCategory.TRANSFORMATION),
    ("regex_extract", OperationCategory.TRANSFORMATION),
    ("regex_mapper", OperationCategory.TRANSFORMATION),
    ("filter", OperationCategory.FILTERING),
    ("conditional_filter", OperationCategory.FILTERING),
    ("duplicate_remove", OperationCategory.FILTERING),
    ("required", OperationCategory.VALIDATION),
    ("type_check", OperationCategory.VALIDATION),
    ("regex_validate", OperationCategory.VALIDATION),
    ("min_value", OperationCategory.VALIDATION),
    ("max_value", OperationCategory.VALIDATION),
    ("allowed_values", OperationCategory.VALIDATION),
    ("unique", OperationCategory.VALIDATION),
    ("fuzzy_match", OperationCategory.MATCHING),
    ("compare", OperationCategory.MATCHING),
    ("count", OperationCategory.AGGREGATION),
    ("sum", OperationCategory.AGGREGATION),
    ("average", OperationCategory.AGGREGATION),
    ("minimum", OperationCategory.AGGREGATION),
    ("maximum", OperationCategory.AGGREGATION),
    ("convert_units", OperationCategory.UNITS),
)

_PROVEN = {"filter", "fuzzy_match", "compare"}
DEFAULT_OPERATIONS = tuple(
    _operation(name, category, proven=name in _PROVEN, mapping=name if name in _PROVEN else "transform")
    for name, category in _SPECS
)
