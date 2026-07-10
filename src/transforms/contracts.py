"""Versioned JSON-compatible contracts for deterministic tabular operations.

This module defines configuration and result shapes only. It contains no
transformation, validation, sorting, or aggregation executors and imports no
runtime internals.
"""

from __future__ import annotations

import math
import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from src.transforms.errors import (
    DUPLICATE_ID,
    DUPLICATE_OUTPUT,
    INVALID_REGEX,
    INVALID_TYPE,
    INVALID_VALUE,
    MISSING_FIELD,
    UNKNOWN_FIELD,
    UNSUPPORTED_VERSION,
    ConfigurationError,
    PathComponent,
)

CONTRACT_VERSION = 1
OPERATION_TYPES = frozenset(
    {"rename", "field_map", "regex_map", "type_coercion", "drop_nulls", "deduplicate", "add_constant", "normalize"}
)
COERCION_TYPES = frozenset(
    {"string", "str", "float", "float64", "number", "int", "int64", "datetime", "timestamp", "bool"}
)
SCALAR_TRANSFORMS = frozenset({"trim", "lower", "upper", "collapse_whitespace"})
MAPPING_ERROR_POLICIES = frozenset({"fail", "null", "default"})
REGEX_FLAGS = {"ASCII": re.ASCII, "IGNORECASE": re.IGNORECASE, "MULTILINE": re.MULTILINE}
VALIDATION_RULE_TYPES = frozenset({"required", "type", "regex", "min", "max", "allowed_values", "unique"})
VALIDATION_SEVERITIES = frozenset({"error", "warning"})
VALIDATION_FAILURE_POLICIES = frozenset({"fail_stage", "report_only"})
SORT_DIRECTIONS = frozenset({"asc", "desc"})
NULL_PLACEMENTS = frozenset({"first", "last"})
AGGREGATION_FUNCTIONS = frozenset({"count", "sum", "avg", "min", "max"})


def _error(code: str, message: str, path: Iterable[PathComponent]) -> ConfigurationError:
    return ConfigurationError(code=code, message=message, path=path)


def _mapping(value: Any, path: tuple[PathComponent, ...]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _error(INVALID_TYPE, "Expected an object.", path)
    return value


def _check_keys(
    payload: Mapping[str, Any],
    *,
    allowed: set[str],
    required: set[str],
    path: tuple[PathComponent, ...],
) -> None:
    for key in required:
        if key not in payload:
            raise _error(MISSING_FIELD, f"Missing required field '{key}'.", (*path, key))
    for key in payload:
        if key not in allowed:
            raise _error(UNKNOWN_FIELD, f"Unknown field '{key}'.", (*path, key))


def _nonempty_string(value: Any, path: tuple[PathComponent, ...]) -> str:
    if not isinstance(value, str):
        raise _error(INVALID_TYPE, "Expected a string.", path)
    if not value.strip():
        raise _error(INVALID_VALUE, "Value must not be empty.", path)
    return value


def _choice(value: Any, choices: frozenset[str], path: tuple[PathComponent, ...]) -> str:
    result = _nonempty_string(value, path)
    if result not in choices:
        expected = ", ".join(sorted(choices))
        raise _error(INVALID_VALUE, f"Unsupported value '{result}'. Expected one of: {expected}.", path)
    return result


def _string_tuple(value: Any, path: tuple[PathComponent, ...]) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise _error(INVALID_TYPE, "Expected an array of strings.", path)
    return tuple(_nonempty_string(item, (*path, index)) for index, item in enumerate(value))


def _json_value(value: Any, path: tuple[PathComponent, ...]) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return deepcopy(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise _error(INVALID_VALUE, "Numeric values must be finite.", path)
        return value
    if isinstance(value, (list, tuple)):
        return [_json_value(item, (*path, index)) for index, item in enumerate(value)]
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise _error(INVALID_TYPE, "Object keys must be strings.", path)
            result[key] = _json_value(item, (*path, key))
        return result
    raise _error(INVALID_TYPE, "Value must be JSON-compatible.", path)


def _version(value: Any, path: tuple[PathComponent, ...]) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise _error(INVALID_TYPE, "contract_version must be an integer.", path)
    if value != CONTRACT_VERSION:
        raise _error(UNSUPPORTED_VERSION, f"Unsupported contract version '{value}'.", path)
    return value


def _repath(exc: ConfigurationError, path: tuple[PathComponent, ...]) -> ConfigurationError:
    return ConfigurationError(exc.code, exc.message, (*path, *exc.path_components))


@dataclass(frozen=True, slots=True)
class OperationDefinition:
    id: str
    type: str
    options: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _nonempty_string(self.id, ("id",)))
        object.__setattr__(self, "type", _choice(self.type, OPERATION_TYPES, ("type",)))
        object.__setattr__(self, "options", _json_value(_mapping(self.options, ("options",)), ("options",)))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], path: tuple[PathComponent, ...] = ()) -> "OperationDefinition":
        data = _mapping(payload, path)
        _check_keys(data, allowed={"id", "type", "options"}, required={"id", "type"}, path=path)
        try:
            return cls(id=data["id"], type=data["type"], options=data.get("options", {}))
        except ConfigurationError as exc:
            raise _repath(exc, path) from exc

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "type": self.type, "options": _json_value(self.options, ("options",))}


@dataclass(frozen=True, slots=True)
class TransformationPlan:
    operations: tuple[OperationDefinition, ...] = ()
    contract_version: int = CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "contract_version", _version(self.contract_version, ("contract_version",)))
        operations = tuple(self.operations)
        if not all(isinstance(item, OperationDefinition) for item in operations):
            raise _error(INVALID_TYPE, "operations must contain OperationDefinition records.", ("operations",))
        seen: set[str] = set()
        for index, operation in enumerate(operations):
            if operation.id in seen:
                raise _error(DUPLICATE_ID, f"Duplicate operation id '{operation.id}'.", ("operations", index, "id"))
            seen.add(operation.id)
        object.__setattr__(self, "operations", operations)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TransformationPlan":
        data = _mapping(payload, ())
        _check_keys(data, allowed={"contract_version", "operations"}, required={"contract_version", "operations"}, path=())
        raw_operations = data["operations"]
        if not isinstance(raw_operations, list):
            raise _error(INVALID_TYPE, "Expected an array.", ("operations",))
        return cls(
            contract_version=_version(data["contract_version"], ("contract_version",)),
            operations=tuple(OperationDefinition.from_dict(item, ("operations", index)) for index, item in enumerate(raw_operations)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"contract_version": self.contract_version, "operations": [item.to_dict() for item in self.operations]}


@dataclass(frozen=True, slots=True)
class FieldMapping:
    source: str
    target: str
    required: bool = False
    default: Any = None
    coerce: str | None = None
    transforms: tuple[str, ...] = ()
    on_error: str = "fail"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _nonempty_string(self.source, ("source",)))
        object.__setattr__(self, "target", _nonempty_string(self.target, ("target",)))
        if not isinstance(self.required, bool):
            raise _error(INVALID_TYPE, "required must be a boolean.", ("required",))
        object.__setattr__(self, "default", _json_value(self.default, ("default",)))
        if self.coerce is not None:
            object.__setattr__(self, "coerce", _choice(self.coerce, COERCION_TYPES, ("coerce",)))
        transforms = _string_tuple(self.transforms, ("transforms",))
        for index, transform in enumerate(transforms):
            _choice(transform, SCALAR_TRANSFORMS, ("transforms", index))
        object.__setattr__(self, "transforms", transforms)
        object.__setattr__(self, "on_error", _choice(self.on_error, MAPPING_ERROR_POLICIES, ("on_error",)))
        if self.on_error == "default" and self.default is None:
            raise _error(INVALID_VALUE, "on_error 'default' requires a non-null default.", ("default",))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], path: tuple[PathComponent, ...] = ()) -> "FieldMapping":
        data = _mapping(payload, path)
        allowed = {"source", "target", "required", "default", "coerce", "transforms", "on_error"}
        _check_keys(data, allowed=allowed, required={"source", "target"}, path=path)
        try:
            return cls(
                source=data["source"], target=data["target"], required=data.get("required", False),
                default=data.get("default"), coerce=data.get("coerce"),
                transforms=tuple(data.get("transforms", ())), on_error=data.get("on_error", "fail"),
            )
        except ConfigurationError as exc:
            raise _repath(exc, path) from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source, "target": self.target, "required": self.required,
            "default": _json_value(self.default, ("default",)), "coerce": self.coerce,
            "transforms": list(self.transforms), "on_error": self.on_error,
        }


@dataclass(frozen=True, slots=True)
class RegexDefinition:
    id: str
    pattern: str
    flags: tuple[str, ...] = ()
    description: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _nonempty_string(self.id, ("id",)))
        pattern = _nonempty_string(self.pattern, ("pattern",))
        flags = _string_tuple(self.flags, ("flags",))
        compiled_flags = 0
        for index, flag_name in enumerate(flags):
            if flag_name not in REGEX_FLAGS:
                raise _error(INVALID_VALUE, f"Unsupported regex flag '{flag_name}'.", ("flags", index))
            compiled_flags |= REGEX_FLAGS[flag_name]
        try:
            compiled = re.compile(pattern, compiled_flags)
        except re.error as exc:
            raise _error(INVALID_REGEX, f"Invalid regular expression: {exc}.", ("pattern",)) from exc
        if not compiled.groupindex:
            raise _error(INVALID_REGEX, "Regex definitions require at least one named capture group.", ("pattern",))
        object.__setattr__(self, "pattern", pattern)
        object.__setattr__(self, "flags", flags)
        if not isinstance(self.description, str):
            raise _error(INVALID_TYPE, "description must be a string.", ("description",))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], path: tuple[PathComponent, ...] = ()) -> "RegexDefinition":
        data = _mapping(payload, path)
        _check_keys(data, allowed={"id", "pattern", "flags", "description"}, required={"id", "pattern"}, path=path)
        try:
            return cls(id=data["id"], pattern=data["pattern"], flags=tuple(data.get("flags", ())), description=data.get("description", ""))
        except ConfigurationError as exc:
            raise _repath(exc, path) from exc

    @property
    def group_names(self) -> tuple[str, ...]:
        flags = sum(REGEX_FLAGS[name] for name in self.flags)
        return tuple(re.compile(self.pattern, flags).groupindex)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "pattern": self.pattern, "flags": list(self.flags), "description": self.description}


@dataclass(frozen=True, slots=True)
class ValidationRule:
    id: str
    type: str
    field: str
    severity: str = "error"
    value: Any = None
    values: tuple[Any, ...] = ()
    pattern_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _nonempty_string(self.id, ("id",)))
        object.__setattr__(self, "type", _choice(self.type, VALIDATION_RULE_TYPES, ("type",)))
        object.__setattr__(self, "field", _nonempty_string(self.field, ("field",)))
        object.__setattr__(self, "severity", _choice(self.severity, VALIDATION_SEVERITIES, ("severity",)))
        object.__setattr__(self, "value", _json_value(self.value, ("value",)))
        object.__setattr__(self, "values", tuple(_json_value(item, ("values", index)) for index, item in enumerate(self.values)))
        if self.pattern_id is not None:
            object.__setattr__(self, "pattern_id", _nonempty_string(self.pattern_id, ("pattern_id",)))
        if self.type in {"min", "max", "type"} and self.value is None:
            raise _error(MISSING_FIELD, f"Rule type '{self.type}' requires value.", ("value",))
        if self.type == "allowed_values" and not self.values:
            raise _error(MISSING_FIELD, "allowed_values requires values.", ("values",))
        if self.type == "regex" and self.pattern_id is None:
            raise _error(MISSING_FIELD, "regex requires pattern_id.", ("pattern_id",))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], path: tuple[PathComponent, ...] = ()) -> "ValidationRule":
        data = _mapping(payload, path)
        allowed = {"id", "type", "field", "severity", "value", "values", "pattern_id"}
        _check_keys(data, allowed=allowed, required={"id", "type", "field"}, path=path)
        if "values" in data and not isinstance(data["values"], list):
            raise _error(INVALID_TYPE, "values must be an array.", (*path, "values"))
        try:
            return cls(
                id=data["id"], type=data["type"], field=data["field"], severity=data.get("severity", "error"),
                value=data.get("value"), values=tuple(data.get("values", ())), pattern_id=data.get("pattern_id"),
            )
        except ConfigurationError as exc:
            raise _repath(exc, path) from exc

    def to_dict(self) -> dict[str, Any]:
        result = {"id": self.id, "type": self.type, "field": self.field, "severity": self.severity}
        if self.value is not None:
            result["value"] = _json_value(self.value, ("value",))
        if self.values:
            result["values"] = [_json_value(item, ("values", index)) for index, item in enumerate(self.values)]
        if self.pattern_id is not None:
            result["pattern_id"] = self.pattern_id
        return result


@dataclass(frozen=True, slots=True)
class ValidationPlan:
    rules: tuple[ValidationRule, ...] = ()
    failure_policy: str = "fail_stage"
    issue_limit: int = 100
    contract_version: int = CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "contract_version", _version(self.contract_version, ("contract_version",)))
        object.__setattr__(self, "failure_policy", _choice(self.failure_policy, VALIDATION_FAILURE_POLICIES, ("failure_policy",)))
        if not isinstance(self.issue_limit, int) or isinstance(self.issue_limit, bool) or self.issue_limit < 1:
            raise _error(INVALID_VALUE, "issue_limit must be a positive integer.", ("issue_limit",))
        rules = tuple(self.rules)
        seen: set[str] = set()
        for index, rule in enumerate(rules):
            if not isinstance(rule, ValidationRule):
                raise _error(INVALID_TYPE, "rules must contain ValidationRule records.", ("rules", index))
            if rule.id in seen:
                raise _error(DUPLICATE_ID, f"Duplicate validation rule id '{rule.id}'.", ("rules", index, "id"))
            seen.add(rule.id)
        object.__setattr__(self, "rules", rules)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ValidationPlan":
        data = _mapping(payload, ())
        _check_keys(data, allowed={"contract_version", "failure_policy", "issue_limit", "rules"}, required={"contract_version", "rules"}, path=())
        raw_rules = data["rules"]
        if not isinstance(raw_rules, list):
            raise _error(INVALID_TYPE, "Expected an array.", ("rules",))
        return cls(
            contract_version=_version(data["contract_version"], ("contract_version",)),
            failure_policy=data.get("failure_policy", "fail_stage"), issue_limit=data.get("issue_limit", 100),
            rules=tuple(ValidationRule.from_dict(item, ("rules", index)) for index, item in enumerate(raw_rules)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version, "failure_policy": self.failure_policy,
            "issue_limit": self.issue_limit, "rules": [rule.to_dict() for rule in self.rules],
        }


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    row_index: int | str
    rule_id: str
    field: str
    severity: str
    message: str
    code: str = "validation_failed"

    def __post_init__(self) -> None:
        if not isinstance(self.row_index, (int, str)) or isinstance(self.row_index, bool):
            raise _error(INVALID_TYPE, "row_index must be an integer or string.", ("row_index",))
        object.__setattr__(self, "rule_id", _nonempty_string(self.rule_id, ("rule_id",)))
        object.__setattr__(self, "field", _nonempty_string(self.field, ("field",)))
        object.__setattr__(self, "severity", _choice(self.severity, VALIDATION_SEVERITIES, ("severity",)))
        object.__setattr__(self, "message", _nonempty_string(self.message, ("message",)))
        object.__setattr__(self, "code", _nonempty_string(self.code, ("code",)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_index": self.row_index,
            "rule_id": self.rule_id,
            "field": self.field,
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ValidationResult:
    valid: bool
    total_rows: int
    valid_rows: int
    invalid_rows: int
    error_count: int
    warning_count: int
    issues: tuple[ValidationIssue, ...] = ()
    truncated: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.valid, bool) or not isinstance(self.truncated, bool):
            raise _error(INVALID_TYPE, "valid and truncated must be booleans.", ())
        for name in ("total_rows", "valid_rows", "invalid_rows", "error_count", "warning_count"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise _error(INVALID_VALUE, f"{name} must be a non-negative integer.", (name,))
        if self.valid_rows + self.invalid_rows != self.total_rows:
            raise _error(INVALID_VALUE, "valid_rows plus invalid_rows must equal total_rows.", ("total_rows",))
        issues = tuple(self.issues)
        if not all(isinstance(issue, ValidationIssue) for issue in issues):
            raise _error(INVALID_TYPE, "issues must contain ValidationIssue records.", ("issues",))
        object.__setattr__(self, "issues", issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid, "total_rows": self.total_rows, "valid_rows": self.valid_rows,
            "invalid_rows": self.invalid_rows, "error_count": self.error_count, "warning_count": self.warning_count,
            "total_issue_count": self.error_count + self.warning_count,
            "detail_count": len(self.issues),
            "issues": [issue.to_dict() for issue in self.issues], "truncated": self.truncated,
        }


# Explicit alias for callers that need to distinguish this result from
# document-structural validation results.
DataValidationResult = ValidationResult


@dataclass(frozen=True, slots=True)
class SortKey:
    field: str
    direction: str = "asc"
    nulls: str = "last"

    def __post_init__(self) -> None:
        object.__setattr__(self, "field", _nonempty_string(self.field, ("field",)))
        object.__setattr__(self, "direction", _choice(self.direction, SORT_DIRECTIONS, ("direction",)))
        object.__setattr__(self, "nulls", _choice(self.nulls, NULL_PLACEMENTS, ("nulls",)))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], path: tuple[PathComponent, ...] = ()) -> "SortKey":
        data = _mapping(payload, path)
        _check_keys(
            data,
            allowed={"field", "direction", "nulls"},
            required={"field", "direction", "nulls"},
            path=path,
        )
        try:
            return cls(field=data["field"], direction=data.get("direction", "asc"), nulls=data.get("nulls", "last"))
        except ConfigurationError as exc:
            raise _repath(exc, path) from exc

    def to_dict(self) -> dict[str, Any]:
        return {"field": self.field, "direction": self.direction, "nulls": self.nulls}


@dataclass(frozen=True, slots=True)
class SortPlan:
    keys: tuple[SortKey, ...]
    stable: bool = True
    contract_version: int = CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "contract_version", _version(self.contract_version, ("contract_version",)))
        keys = tuple(self.keys)
        if not keys:
            raise _error(MISSING_FIELD, "At least one sort key is required.", ("keys",))
        if not all(isinstance(key, SortKey) for key in keys):
            raise _error(INVALID_TYPE, "keys must contain SortKey records.", ("keys",))
        if not isinstance(self.stable, bool):
            raise _error(INVALID_TYPE, "stable must be a boolean.", ("stable",))
        if not self.stable:
            raise _error(INVALID_VALUE, "Sort plans must use stable sorting.", ("stable",))
        seen_fields: set[str] = set()
        for index, key in enumerate(keys):
            if key.field in seen_fields:
                raise _error(DUPLICATE_ID, f"Duplicate sort field '{key.field}'.", ("keys", index, "field"))
            seen_fields.add(key.field)
        object.__setattr__(self, "keys", keys)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SortPlan":
        data = _mapping(payload, ())
        _check_keys(data, allowed={"contract_version", "keys", "stable"}, required={"contract_version", "keys"}, path=())
        raw_keys = data["keys"]
        if not isinstance(raw_keys, list):
            raise _error(INVALID_TYPE, "Expected an array.", ("keys",))
        return cls(
            contract_version=_version(data["contract_version"], ("contract_version",)),
            keys=tuple(SortKey.from_dict(item, ("keys", index)) for index, item in enumerate(raw_keys)),
            stable=data.get("stable", True),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"contract_version": self.contract_version, "keys": [key.to_dict() for key in self.keys], "stable": self.stable}


@dataclass(frozen=True, slots=True)
class AggregationDefinition:
    field: str | None
    function: str
    output: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "function", _choice(self.function, AGGREGATION_FUNCTIONS, ("function",)))
        object.__setattr__(self, "output", _nonempty_string(self.output, ("output",)))
        if self.field is not None:
            object.__setattr__(self, "field", _nonempty_string(self.field, ("field",)))
        if self.function != "count" and self.field is None:
            raise _error(MISSING_FIELD, f"Aggregation '{self.function}' requires field.", ("field",))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], path: tuple[PathComponent, ...] = ()) -> "AggregationDefinition":
        data = _mapping(payload, path)
        _check_keys(
            data,
            allowed={"field", "function", "output"},
            required={"function", "output"},
            path=path,
        )
        try:
            return cls(function=data["function"], output=data["output"], field=data.get("field"))
        except ConfigurationError as exc:
            raise _repath(exc, path) from exc

    def to_dict(self) -> dict[str, Any]:
        return {"field": self.field, "function": self.function, "output": self.output}


@dataclass(frozen=True, slots=True)
class AggregationPlan:
    aggregations: tuple[AggregationDefinition, ...]
    group_by: tuple[str, ...] = ()
    drop_null_groups: bool = False
    contract_version: int = CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "contract_version", _version(self.contract_version, ("contract_version",)))
        group_by = _string_tuple(self.group_by, ("group_by",))
        if len(set(group_by)) != len(group_by):
            raise _error(DUPLICATE_ID, "group_by fields must be unique.", ("group_by",))
        aggregations = tuple(self.aggregations)
        if not aggregations:
            raise _error(MISSING_FIELD, "At least one aggregation is required.", ("aggregations",))
        outputs: set[str] = set()
        for index, aggregation in enumerate(aggregations):
            if not isinstance(aggregation, AggregationDefinition):
                raise _error(INVALID_TYPE, "aggregations must contain AggregationDefinition records.", ("aggregations", index))
            if aggregation.output in outputs:
                raise _error(DUPLICATE_OUTPUT, f"Duplicate aggregation output '{aggregation.output}'.", ("aggregations", index, "output"))
            outputs.add(aggregation.output)
            if aggregation.output in group_by:
                raise _error(
                    DUPLICATE_OUTPUT,
                    f"Aggregation output '{aggregation.output}' conflicts with group_by.",
                    ("aggregations", index, "output"),
                )
        if not isinstance(self.drop_null_groups, bool):
            raise _error(INVALID_TYPE, "drop_null_groups must be a boolean.", ("drop_null_groups",))
        object.__setattr__(self, "group_by", group_by)
        object.__setattr__(self, "aggregations", aggregations)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AggregationPlan":
        data = _mapping(payload, ())
        _check_keys(data, allowed={"contract_version", "group_by", "aggregations", "drop_null_groups"}, required={"contract_version", "aggregations"}, path=())
        raw_aggregations = data["aggregations"]
        if not isinstance(raw_aggregations, list):
            raise _error(INVALID_TYPE, "Expected an array.", ("aggregations",))
        raw_group_by = data.get("group_by", [])
        if not isinstance(raw_group_by, list):
            raise _error(INVALID_TYPE, "group_by must be an array.", ("group_by",))
        return cls(
            contract_version=_version(data["contract_version"], ("contract_version",)),
            group_by=tuple(raw_group_by),
            aggregations=tuple(AggregationDefinition.from_dict(item, ("aggregations", index)) for index, item in enumerate(raw_aggregations)),
            drop_null_groups=data.get("drop_null_groups", False),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version, "group_by": list(self.group_by),
            "aggregations": [item.to_dict() for item in self.aggregations], "drop_null_groups": self.drop_null_groups,
        }
