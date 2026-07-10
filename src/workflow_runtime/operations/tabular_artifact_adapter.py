"""Workflow-owned adapter for supported tabular input artifacts."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pandas as pd


class UnsupportedTabularArtifactError(TypeError):
    """Raised when a workflow artifact has no approved tabular adapter."""


def to_dataframe(input_artifact: Any) -> pd.DataFrame:
    """Return an isolated DataFrame for approved artifact types."""
    if isinstance(input_artifact, pd.DataFrame):
        return input_artifact.copy(deep=True)
    if isinstance(input_artifact, list) and all(isinstance(row, dict) for row in input_artifact):
        return pd.DataFrame(deepcopy(input_artifact))
    raise UnsupportedTabularArtifactError(
        "TransformStage supports only pandas DataFrame or list[dict] input artifacts."
    )

