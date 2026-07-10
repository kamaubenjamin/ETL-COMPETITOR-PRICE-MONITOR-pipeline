"""Deterministic, bounded, privacy-safe tabular data validation."""

from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import date, datetime
from numbers import Integral, Real
from typing import Any

import pandas as pd

from src.transforms.contracts import (
    DataValidationResult,
    ValidationIssue,
    ValidationPlan,
    ValidationRule,
)
from src.transforms.errors import ConfigurationError
from src.transforms.regex_registry import RegexRegistry

SUPPORTED_DATA_TYPES = frozenset(
    {"string", "str", "number", "float", "int", "integer", "bool", "boolean", "datetime", "timestamp"}
)

_ISSUE_DETAILS = {
    "required": ("required_missing", "Required field is missing."),
    "type": ("type_mismatch", "Field does not match the required type."),
    "regex": ("regex_mismatch", "Field does not match the required pattern."),
    "min": ("min_violation", "Field is below the configured minimum."),
    "max": ("max_violation", "Field is above the configured maximum."),
    "allowed_values": ("value_not_allowed", "Field is not in the allowed value set."),
    "unique": ("duplicate_value", "Field value is duplicated."),
}


def _is_null(value: Any) -> bool:
    marker = pd.isna(value)
    try:
        return bool(marker)
    except (TypeError, ValueError):
        return False


def _is_required_missing(value: Any) -> bool:
    return _is_null(value) or (isinstance(value, str) and not value.strip())


def _is_type(value: Any, expected: str) -> bool:
    if expected in {"string", "str"}:
        return isinstance(value, str)
    if expected in {"bool", "boolean"}:
        return isinstance(value, bool)
    if expected in {"int", "integer"}:
        return isinstance(value, Integral) and not isinstance(value, bool)
    if expected == "float":
        return isinstance(value, Real) and not isinstance(value, (Integral, bool)) and math.isfinite(float(value))
    if expected == "number":
        return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(float(value))
    if expected in {"datetime", "timestamp"}:
        return isinstance(value, (datetime, date, pd.Timestamp))
    return False


def _equal(left: Any, right: Any) -> bool:
    try:
        result = left == right
        return bool(result)
    except (TypeError, ValueError):
        return False


class TabularDataValidator:
    """Validate a DataFrame without mutating it or retaining unbounded issues."""

    def __init__(self, *, regex_registry: RegexRegistry | None = None) -> None:
        self._regex_registry = regex_registry or RegexRegistry()

    def validate(
        self,
        frame: pd.DataFrame,
        plan: ValidationPlan | Mapping[str, Any],
    ) -> DataValidationResult:
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("TabularDataValidator requires a pandas DataFrame.")
        parsed_plan = plan if isinstance(plan, ValidationPlan) else ValidationPlan.from_dict(plan)
        self._preflight(frame, parsed_plan)
        working = frame.copy(deep=True)

        details: list[ValidationIssue] = []
        error_count = 0
        warning_count = 0
        error_rows: set[int] = set()

        for rule in parsed_plan.rules:
            failing_positions = self._failing_positions(working, rule)
            code, message = _ISSUE_DETAILS[rule.type]
            for position in failing_positions:
                if rule.severity == "error":
                    error_count += 1
                    error_rows.add(position)
                else:
                    warning_count += 1
                if len(details) < parsed_plan.issue_limit:
                    details.append(
                        ValidationIssue(
                            row_index=position,
                            rule_id=rule.id,
                            field=rule.field,
                            severity=rule.severity,
                            code=code,
                            message=message,
                        )
                    )

        total_rows = len(working)
        invalid_rows = len(error_rows)
        total_issue_count = error_count + warning_count
        return DataValidationResult(
            valid=error_count == 0,
            total_rows=total_rows,
            valid_rows=total_rows - invalid_rows,
            invalid_rows=invalid_rows,
            error_count=error_count,
            warning_count=warning_count,
            issues=tuple(details),
            truncated=total_issue_count > len(details),
        )

    def _preflight(self, frame: pd.DataFrame, plan: ValidationPlan) -> None:
        columns = set(frame.columns)
        for index, rule in enumerate(plan.rules):
            path = ("rules", index)
            if rule.field not in columns:
                raise ConfigurationError(
                    "missing_column",
                    f"Validation field '{rule.field}' is missing.",
                    (*path, "field"),
                )
            if rule.type == "type":
                if not isinstance(rule.value, str) or rule.value not in SUPPORTED_DATA_TYPES:
                    raise ConfigurationError(
                        "invalid_value",
                        "Unsupported validation data type.",
                        (*path, "value"),
                    )
            elif rule.type == "regex":
                self._regex_registry.resolve(rule.pattern_id or "", (*path, "pattern_id"))
            elif rule.type in {"min", "max"}:
                if (
                    not isinstance(rule.value, Real)
                    or isinstance(rule.value, bool)
                    or not math.isfinite(float(rule.value))
                ):
                    raise ConfigurationError(
                        "invalid_value",
                        f"{rule.type} requires a finite numeric value.",
                        (*path, "value"),
                    )

    def _failing_positions(self, frame: pd.DataFrame, rule: ValidationRule) -> list[int]:
        series = frame[rule.field]
        if rule.type == "unique":
            return self._duplicate_positions(series)

        failures: list[int] = []
        pattern = self._regex_registry.compiled(rule.pattern_id or "") if rule.type == "regex" else None
        for position, value in enumerate(series.tolist()):
            if rule.type == "required":
                failed = _is_required_missing(value)
            elif _is_null(value):
                failed = False
            elif rule.type == "type":
                failed = not _is_type(value, str(rule.value))
            elif rule.type == "regex":
                failed = not isinstance(value, str) or pattern is None or pattern.search(value) is None
            elif rule.type == "min":
                try:
                    failed = value < rule.value
                except (TypeError, ValueError):
                    failed = True
            elif rule.type == "max":
                try:
                    failed = value > rule.value
                except (TypeError, ValueError):
                    failed = True
            elif rule.type == "allowed_values":
                failed = not any(_equal(value, allowed) for allowed in rule.values)
            else:
                failed = False
            if failed:
                failures.append(position)
        return failures

    @staticmethod
    def _duplicate_positions(series: pd.Series) -> list[int]:
        groups: list[tuple[Any, list[int]]] = []
        for position, value in enumerate(series.tolist()):
            if _is_null(value):
                continue
            for representative, positions in groups:
                if _equal(value, representative):
                    positions.append(position)
                    break
            else:
                groups.append((value, [position]))
        return sorted(
            position
            for _, positions in groups
            if len(positions) > 1
            for position in positions
        )


def validate_data(
    frame: pd.DataFrame,
    plan: ValidationPlan | Mapping[str, Any],
    *,
    regex_registry: RegexRegistry | None = None,
) -> DataValidationResult:
    """Convenience entry point for deterministic tabular validation."""
    return TabularDataValidator(regex_registry=regex_registry).validate(frame, plan)
