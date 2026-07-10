"""Deterministic flat-field mapping and coercion helpers."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import pandas as pd

from src.transforms.contracts import FieldMapping
from src.transforms.errors import ConfigurationError

_TRUE_VALUES = frozenset({"true", "1", "yes", "y"})
_FALSE_VALUES = frozenset({"false", "0", "no", "n"})


def parse_field_mappings(
    payloads: Any,
    path: tuple[str | int, ...] = ("mappings",),
) -> tuple[FieldMapping, ...]:
    if not isinstance(payloads, list):
        raise ConfigurationError("invalid_type", "mappings must be an array.", path)
    return tuple(
        FieldMapping.from_dict(payload, (*path, index))
        for index, payload in enumerate(payloads)
    )


def validate_field_mappings(
    mappings: Sequence[FieldMapping],
    columns: Iterable[str],
    path: tuple[str | int, ...] = ("mappings",),
) -> tuple[str, ...]:
    """Validate source preconditions and return the resulting column schema."""
    resulting = list(columns)
    available = set(resulting)
    targets: set[str] = set()
    for index, mapping in enumerate(mappings):
        if mapping.target in targets:
            raise ConfigurationError(
                "duplicate_output",
                f"Duplicate field mapping target '{mapping.target}'.",
                (*path, index, "target"),
            )
        targets.add(mapping.target)
        if mapping.required and mapping.source not in available:
            raise ConfigurationError(
                "missing_column",
                f"Required source column '{mapping.source}' is missing.",
                (*path, index, "source"),
            )
        if mapping.target not in available:
            resulting.append(mapping.target)
            available.add(mapping.target)
    return tuple(resulting)


def _invalid_mask(original: pd.Series, converted: pd.Series) -> pd.Series:
    return original.notna() & converted.isna()


def _coerce_bool(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    converted = pd.Series(pd.NA, index=series.index, dtype="boolean")
    invalid = pd.Series(False, index=series.index, dtype=bool)
    for index, value in series.items():
        if pd.isna(value):
            continue
        if isinstance(value, bool):
            converted.at[index] = value
            continue
        normalized = str(value).strip().lower()
        if normalized in _TRUE_VALUES:
            converted.at[index] = True
        elif normalized in _FALSE_VALUES:
            converted.at[index] = False
        else:
            invalid.at[index] = True
    return converted, invalid


def coerce_series(
    series: pd.Series,
    dtype: str,
    *,
    on_error: str = "fail",
    default: Any = None,
    path: tuple[str | int, ...] = ("coerce",),
) -> pd.Series:
    """Coerce a series with deterministic, privacy-safe failure behavior."""
    if dtype in {"string", "str"}:
        converted = series.astype("string")
        invalid = pd.Series(False, index=series.index, dtype=bool)
    elif dtype in {"float", "float64", "number"}:
        converted = pd.to_numeric(series, errors="coerce").astype("float64")
        invalid = _invalid_mask(series, converted)
    elif dtype in {"int", "int64"}:
        numeric = pd.to_numeric(series, errors="coerce")
        integral = numeric.isna() | (numeric % 1 == 0)
        invalid = _invalid_mask(series, numeric) | ~integral
        numeric = numeric.mask(~integral)
        converted = numeric.astype("Int64")
    elif dtype in {"datetime", "timestamp"}:
        converted = pd.to_datetime(series, errors="coerce")
        invalid = _invalid_mask(series, converted)
    elif dtype == "bool":
        converted, invalid = _coerce_bool(series)
    else:
        raise ConfigurationError("invalid_value", f"Unsupported coercion '{dtype}'.", path)

    if invalid.any():
        if on_error == "fail":
            raise ConfigurationError(
                "coercion_failed",
                "One or more values could not be coerced.",
                path,
            )
        if on_error == "default":
            converted = converted.copy()
            converted.loc[invalid] = default
    return converted


def _apply_scalar_transform(series: pd.Series, transform: str) -> pd.Series:
    def apply_value(value: Any) -> Any:
        if pd.isna(value):
            return value
        text = str(value)
        if transform == "trim":
            return text.strip()
        if transform == "lower":
            return text.lower()
        if transform == "upper":
            return text.upper()
        if transform == "collapse_whitespace":
            return re.sub(r"\s+", " ", text).strip()
        raise ConfigurationError("invalid_value", f"Unsupported scalar transform '{transform}'.")

    return series.map(apply_value)


def apply_field_mappings(
    frame: pd.DataFrame,
    mappings: Sequence[FieldMapping],
) -> pd.DataFrame:
    """Apply validated mappings in order to a copied DataFrame."""
    validate_field_mappings(mappings, frame.columns)
    result = frame.copy(deep=True)
    for index, mapping in enumerate(mappings):
        path = ("mappings", index)
        if mapping.source in result.columns:
            series = result[mapping.source].copy()
        else:
            series = pd.Series(mapping.default, index=result.index)

        for transform in mapping.transforms:
            series = _apply_scalar_transform(series, transform)

        if mapping.coerce is not None:
            series = coerce_series(
                series,
                mapping.coerce,
                on_error=mapping.on_error,
                default=mapping.default,
                path=(*path, "coerce"),
            )

        if mapping.default is not None:
            series = series.fillna(mapping.default)
        result[mapping.target] = series
    return result
