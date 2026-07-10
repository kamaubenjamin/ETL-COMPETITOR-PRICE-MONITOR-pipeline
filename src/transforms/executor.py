"""Canonical deterministic executor for versioned transformation plans."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from src.contracts.records import CANONICAL_PRODUCT_COLUMNS
from src.transforms.contracts import COERCION_TYPES, FieldMapping, OperationDefinition, TransformationPlan
from src.transforms.errors import ConfigurationError
from src.transforms.field_mapping import (
    apply_field_mappings,
    coerce_series,
    parse_field_mappings,
    validate_field_mappings,
)
from src.transforms.product_identity import normalize_product_frame
from src.transforms.regex_registry import RegexRegistry
from src.transforms.registry import DEFAULT_OPERATION_REGISTRY, OperationRegistry

Path = tuple[str | int, ...]


def _options(operation: OperationDefinition) -> Mapping[str, Any]:
    return operation.options


def _check_options(
    options: Mapping[str, Any],
    *,
    allowed: set[str],
    required: set[str],
    path: Path,
) -> None:
    for key in required:
        if key not in options:
            raise ConfigurationError("missing_field", f"Missing required option '{key}'.", (*path, key))
    for key in options:
        if key not in allowed:
            raise ConfigurationError("unknown_field", f"Unknown option '{key}'.", (*path, key))


def _column_name(value: Any, path: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError("invalid_type", "Column names must be non-empty strings.", path)
    return value


def _subset(value: Any, path: Path) -> tuple[str, ...] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return (_column_name(value, path),)
    if isinstance(value, list):
        return tuple(_column_name(item, (*path, index)) for index, item in enumerate(value))
    raise ConfigurationError("invalid_type", "subset must be a string, array, or null.", path)


def _require_columns(
    columns: Sequence[str],
    required: Sequence[str],
    path: Path,
    *,
    indexed: bool = False,
) -> None:
    available = set(columns)
    for index, column in enumerate(required):
        if column not in available:
            suffix = (index,) if indexed else ()
            raise ConfigurationError(
                "missing_column",
                f"Required column '{column}' is missing.",
                (*path, *suffix),
            )


class TransformationExecutor:
    """Preflight and execute a versioned transformation plan on a copy."""

    def __init__(
        self,
        *,
        operation_registry: OperationRegistry = DEFAULT_OPERATION_REGISTRY,
        regex_registry: RegexRegistry | None = None,
    ) -> None:
        self._operation_registry = operation_registry
        self._regex_registry = regex_registry or RegexRegistry()

    def execute(
        self,
        frame: pd.DataFrame,
        plan: TransformationPlan | Mapping[str, Any],
    ) -> pd.DataFrame:
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("TransformationExecutor requires a pandas DataFrame.")
        parsed_plan = plan if isinstance(plan, TransformationPlan) else TransformationPlan.from_dict(plan)
        self._preflight(parsed_plan, tuple(str(column) for column in frame.columns))

        result = frame.copy(deep=True)
        for index, operation in enumerate(parsed_plan.operations):
            try:
                result = self._apply(result, operation)
            except ConfigurationError as exc:
                raise ConfigurationError(
                    exc.code,
                    exc.message,
                    ("operations", index, "options", *exc.path_components),
                ) from exc
        return result

    def _preflight(self, plan: TransformationPlan, initial_columns: tuple[str, ...]) -> None:
        columns = list(initial_columns)
        for index, operation in enumerate(plan.operations):
            operation_path = ("operations", index)
            options_path = (*operation_path, "options")
            self._operation_registry.require(operation.type, (*operation_path, "type"))
            options = _options(operation)

            if operation.type == "rename":
                _check_options(options, allowed={"columns"}, required={"columns"}, path=options_path)
                raw_columns = options["columns"]
                if not isinstance(raw_columns, Mapping):
                    raise ConfigurationError("invalid_type", "columns must be an object.", (*options_path, "columns"))
                rename_map: dict[str, str] = {}
                for source, target in raw_columns.items():
                    source_name = _column_name(source, (*options_path, "columns"))
                    target_name = _column_name(target, (*options_path, "columns", source_name))
                    rename_map[source_name] = target_name
                _require_columns(columns, tuple(rename_map), (*options_path, "columns"))
                untouched = set(columns) - set(rename_map)
                for source, target in rename_map.items():
                    if target in untouched:
                        raise ConfigurationError(
                            "duplicate_output",
                            f"Rename target '{target}' already exists.",
                            (*options_path, "columns", source),
                        )
                columns = [rename_map.get(column, column) for column in columns]

            elif operation.type == "field_map":
                _check_options(options, allowed={"mappings"}, required={"mappings"}, path=options_path)
                mappings = parse_field_mappings(options["mappings"], (*options_path, "mappings"))
                columns = list(validate_field_mappings(mappings, columns, (*options_path, "mappings")))

            elif operation.type == "regex_map":
                allowed = {"source", "target", "pattern_id", "group", "on_no_match", "default"}
                required = {"source", "target", "pattern_id", "group"}
                _check_options(options, allowed=allowed, required=required, path=options_path)
                source = _column_name(options["source"], (*options_path, "source"))
                target = _column_name(options["target"], (*options_path, "target"))
                pattern_id = _column_name(options["pattern_id"], (*options_path, "pattern_id"))
                group = _column_name(options["group"], (*options_path, "group"))
                _require_columns(columns, (source,), (*options_path, "source"))
                self._regex_registry.resolve(pattern_id, (*options_path, "pattern_id"))
                self._regex_registry.validate_group(pattern_id, group, (*options_path, "group"))
                policy = options.get("on_no_match", "null")
                if not isinstance(policy, str) or policy not in {"null", "keep", "default", "fail"}:
                    raise ConfigurationError("invalid_value", f"Unsupported on_no_match policy '{policy}'.", (*options_path, "on_no_match"))
                if policy == "default" and "default" not in options:
                    raise ConfigurationError("missing_field", "on_no_match 'default' requires default.", (*options_path, "default"))
                if target not in columns:
                    columns.append(target)

            elif operation.type == "type_coercion":
                _check_options(options, allowed={"columns", "on_error"}, required={"columns"}, path=options_path)
                raw_columns = options["columns"]
                if not isinstance(raw_columns, Mapping):
                    raise ConfigurationError("invalid_type", "columns must be an object.", (*options_path, "columns"))
                for column, dtype in raw_columns.items():
                    name = _column_name(column, (*options_path, "columns"))
                    _require_columns(columns, (name,), (*options_path, "columns", name))
                    if not isinstance(dtype, str) or dtype not in COERCION_TYPES:
                        raise ConfigurationError("invalid_value", f"Unsupported coercion '{dtype}'.", (*options_path, "columns", name))
                on_error = options.get("on_error", "fail")
                if not isinstance(on_error, str) or on_error not in {"fail", "null"}:
                    raise ConfigurationError("invalid_value", "on_error must be 'fail' or 'null'.", (*options_path, "on_error"))

            elif operation.type == "drop_nulls":
                _check_options(options, allowed={"subset"}, required=set(), path=options_path)
                subset = _subset(options.get("subset"), (*options_path, "subset"))
                if subset is not None:
                    _require_columns(columns, subset, (*options_path, "subset"), indexed=True)

            elif operation.type == "deduplicate":
                _check_options(options, allowed={"subset", "keep"}, required=set(), path=options_path)
                subset = _subset(options.get("subset"), (*options_path, "subset"))
                if subset is not None:
                    _require_columns(columns, subset, (*options_path, "subset"), indexed=True)
                keep = options.get("keep", "first")
                if keep is not False and (not isinstance(keep, str) or keep not in {"first", "last"}):
                    raise ConfigurationError("invalid_value", "keep must be 'first', 'last', or false.", (*options_path, "keep"))

            elif operation.type == "add_constant":
                _check_options(options, allowed={"column", "value"}, required={"column", "value"}, path=options_path)
                column = _column_name(options["column"], (*options_path, "column"))
                if column not in columns:
                    columns.append(column)

            elif operation.type == "normalize":
                _check_options(options, allowed={"source", "url"}, required=set(), path=options_path)
                for key in ("source", "url"):
                    if options.get(key) is not None and not isinstance(options[key], str):
                        raise ConfigurationError("invalid_type", f"{key} must be a string or null.", (*options_path, key))
                for column in CANONICAL_PRODUCT_COLUMNS:
                    if column not in columns:
                        columns.append(column)

    def _apply(self, frame: pd.DataFrame, operation: OperationDefinition) -> pd.DataFrame:
        options = _options(operation)
        if operation.type == "rename":
            return frame.rename(columns=dict(options["columns"])).copy(deep=True)
        if operation.type == "field_map":
            mappings: tuple[FieldMapping, ...] = parse_field_mappings(options["mappings"])
            return apply_field_mappings(frame, mappings)
        if operation.type == "regex_map":
            result = frame.copy(deep=True)
            result[options["target"]] = self._regex_registry.map_series(
                result[options["source"]],
                pattern_id=options["pattern_id"],
                group=options["group"],
                on_no_match=options.get("on_no_match", "null"),
                default=options.get("default"),
            )
            return result
        if operation.type == "type_coercion":
            result = frame.copy(deep=True)
            for column, dtype in options["columns"].items():
                result[column] = coerce_series(
                    result[column], dtype, on_error=options.get("on_error", "fail"), path=("columns", column)
                )
            return result
        if operation.type == "drop_nulls":
            return frame.dropna(subset=options.get("subset")).copy(deep=True)
        if operation.type == "deduplicate":
            return frame.drop_duplicates(subset=options.get("subset"), keep=options.get("keep", "first")).copy(deep=True)
        if operation.type == "add_constant":
            result = frame.copy(deep=True)
            result[options["column"]] = options["value"]
            return result
        if operation.type == "normalize":
            had_timestamp = "timestamp" in frame.columns
            result = normalize_product_frame(frame, source=options.get("source"), url=options.get("url"))
            if not had_timestamp:
                result["timestamp"] = None
            return result
        raise ConfigurationError("unknown_operation", f"Unsupported operation '{operation.type}'.", ("type",))
