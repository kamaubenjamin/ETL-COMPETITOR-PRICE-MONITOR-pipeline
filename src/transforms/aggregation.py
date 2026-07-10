"""Deterministic grouped and dataset-level tabular aggregation."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from numbers import Real
from typing import Any

import pandas as pd
from pandas.api.types import is_bool_dtype, is_numeric_dtype

from src.transforms.contracts import AggregationDefinition, AggregationPlan
from src.transforms.errors import ConfigurationError


def _is_null(value: Any) -> bool:
    marker = pd.isna(value)
    try:
        return bool(marker)
    except (TypeError, ValueError):
        return False


def _sortable_group_value(value: Any) -> tuple[int, str, Any]:
    if _is_null(value):
        return (1, "", "")
    if isinstance(value, Real) and not isinstance(value, bool):
        return (0, "number", float(value))
    if isinstance(value, str):
        return (0, "string", value)
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return (0, "datetime", pd.Timestamp(value).isoformat())
    return (0, type(value).__name__, repr(value))


def _group_sort_key(key: tuple[Any, ...]) -> tuple[tuple[int, str, Any], ...]:
    return tuple(_sortable_group_value(value) for value in key)


def _validate_plan(frame: pd.DataFrame, plan: AggregationPlan) -> None:
    for index, field in enumerate(plan.group_by):
        if field not in frame.columns:
            raise ConfigurationError(
                "missing_column",
                f"Group field '{field}' is missing.",
                ("group_by", index),
            )
        for value in frame[field].dropna():
            try:
                hash(value)
            except TypeError as exc:
                raise ConfigurationError(
                    "incompatible_type",
                    f"Group field '{field}' contains unhashable values.",
                    ("group_by", index),
                ) from exc

    for index, aggregation in enumerate(plan.aggregations):
        if aggregation.field is None:
            continue
        if aggregation.field not in frame.columns:
            raise ConfigurationError(
                "missing_column",
                f"Aggregation field '{aggregation.field}' is missing.",
                ("aggregations", index, "field"),
            )
        series = frame[aggregation.field]
        if aggregation.function in {"sum", "avg"} and (
            not is_numeric_dtype(series.dtype) or is_bool_dtype(series.dtype)
        ):
            raise ConfigurationError(
                "incompatible_type",
                f"Aggregation '{aggregation.function}' requires a numeric field.",
                ("aggregations", index, "field"),
            )
        if aggregation.function in {"min", "max"}:
            non_null = series.dropna()
            if not non_null.empty:
                try:
                    non_null.min() if aggregation.function == "min" else non_null.max()
                except (TypeError, ValueError) as exc:
                    raise ConfigurationError(
                        "incompatible_type",
                        f"Aggregation '{aggregation.function}' requires comparable values.",
                        ("aggregations", index, "field"),
                    ) from exc


def _aggregate_series(group: pd.DataFrame, aggregation: AggregationDefinition) -> Any:
    if aggregation.function == "count" and aggregation.field is None:
        return int(len(group))
    series = group[aggregation.field]  # type: ignore[index]
    non_null = series.dropna()
    if aggregation.function == "count":
        return int(non_null.count())
    if non_null.empty:
        return pd.NA
    if aggregation.function == "sum":
        return non_null.sum()
    if aggregation.function == "avg":
        return non_null.mean()
    if aggregation.function == "min":
        return non_null.min()
    if aggregation.function == "max":
        return non_null.max()
    raise ConfigurationError(
        "unsupported_function",
        f"Unsupported aggregation function '{aggregation.function}'.",
    )


def _groups(frame: pd.DataFrame, plan: AggregationPlan) -> list[tuple[tuple[Any, ...], pd.DataFrame]]:
    if not plan.group_by:
        return [((), frame)]
    if frame.empty:
        return []
    grouper: str | list[str] = plan.group_by[0] if len(plan.group_by) == 1 else list(plan.group_by)
    grouped = frame.groupby(grouper, dropna=plan.drop_null_groups, sort=False)
    records: list[tuple[tuple[Any, ...], pd.DataFrame]] = []
    for raw_key, group in grouped:
        key = raw_key if isinstance(raw_key, tuple) else (raw_key,)
        records.append((key, group))
    return sorted(records, key=lambda item: _group_sort_key(item[0]))


def aggregate_data(
    frame: pd.DataFrame,
    plan: AggregationPlan | Mapping[str, Any],
) -> pd.DataFrame:
    """Aggregate a copied DataFrame into a deterministic explicit schema."""
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("aggregate_data requires a pandas DataFrame.")
    parsed_plan = plan if isinstance(plan, AggregationPlan) else AggregationPlan.from_dict(plan)
    _validate_plan(frame, parsed_plan)
    working = frame.copy(deep=True)
    rows: list[dict[str, Any]] = []
    for key, group in _groups(working, parsed_plan):
        row = {field: key[index] for index, field in enumerate(parsed_plan.group_by)}
        for aggregation in parsed_plan.aggregations:
            row[aggregation.output] = _aggregate_series(group, aggregation)
        rows.append(row)
    output_columns = [*parsed_plan.group_by, *(item.output for item in parsed_plan.aggregations)]
    return pd.DataFrame(rows, columns=output_columns)
