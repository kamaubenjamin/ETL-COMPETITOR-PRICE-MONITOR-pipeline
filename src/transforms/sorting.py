"""Deterministic stable sorting for tabular artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from src.transforms.contracts import SortPlan
from src.transforms.errors import ConfigurationError


def sort_data(
    frame: pd.DataFrame,
    plan: SortPlan | Mapping[str, Any],
) -> pd.DataFrame:
    """Apply stable sorting with independent null placement per key."""
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("sort_data requires a pandas DataFrame.")
    parsed_plan = plan if isinstance(plan, SortPlan) else SortPlan.from_dict(plan)
    missing = [key.field for key in parsed_plan.keys if key.field not in frame.columns]
    if missing:
        first = next(index for index, key in enumerate(parsed_plan.keys) if key.field == missing[0])
        raise ConfigurationError(
            "missing_column",
            f"Sort field '{missing[0]}' is missing.",
            ("keys", first, "field"),
        )

    result = frame.copy(deep=True)
    # Stable right-to-left passes preserve lexicographic priority while allowing
    # each key to choose its own null placement.
    for key in reversed(parsed_plan.keys):
        try:
            result = result.sort_values(
                by=key.field,
                ascending=key.direction == "asc",
                na_position=key.nulls,
                kind="mergesort",
            )
        except TypeError as exc:
            raise ConfigurationError(
                "incompatible_type",
                f"Sort field '{key.field}' contains incompatible values.",
                ("keys", next(i for i, item in enumerate(parsed_plan.keys) if item is key), "field"),
            ) from exc
    return result.copy(deep=True)

