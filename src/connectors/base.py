"""
Standard connector contract.

All connectors expose the same lifecycle: validate -> extract -> transform ->
normalize -> load. The load hook is intentionally a no-op by default because
the execution engine still owns persistence. Future distributed connectors can
override it to stream batches to Kafka or object storage.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import pandas as pd

from src.contracts.records import CANONICAL_PRODUCT_COLUMNS, normalize_product_frame
from src.core.logging import ExecutionLogger


class ConnectorValidationError(ValueError):
    """Raised when connector configuration or output is invalid."""


@dataclass
class BaseConnector:
    source_name: Optional[str] = None
    source_type: str = "base"
    url: Optional[str] = None
    selector: Optional[str] = None
    mode: Optional[str] = None
    keyword: Optional[str] = None
    run_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    logger: ExecutionLogger = field(default_factory=ExecutionLogger)

    def extract(self) -> pd.DataFrame:
        raise NotImplementedError("Connector must implement extract()")

    def validate(self) -> None:
        """Validate connector configuration before extraction."""

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Connector-local transformation hook."""
        return df

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        return normalize_product_frame(
            df,
            source=self.source_name or self.source_type,
            url=self.url,
        )

    def load(self, df: pd.DataFrame) -> pd.DataFrame:
        """Persistence stays in the execution engine; return df unchanged."""
        return df

    def run(self) -> pd.DataFrame:
        scoped_logger = self.logger.bind(run_id=self.run_id, connector_type=self.source_type)
        scoped_logger.info("connector_started", event="connector_started", source_name=self.source_name)
        self.validate()
        df = self.extract()
        df = self.validate_output(df)
        df = self.transform(df)
        df = self.normalize(df)
        df = self.validate_output(df, require_canonical=True)
        df = self.load(df)
        scoped_logger.info(
            "connector_finished",
            event="connector_finished",
            source_name=self.source_name,
            records_processed=len(df),
        )
        return df

    def validate_output(self, df: pd.DataFrame, *, require_canonical: bool = False) -> pd.DataFrame:
        if df is None:
            raise ConnectorValidationError("Connector returned None")
        if not isinstance(df, pd.DataFrame):
            raise ConnectorValidationError("Connector must return a pandas DataFrame")
        if df.empty:
            raise ConnectorValidationError("Connector returned empty DataFrame")
        if require_canonical:
            missing = [column for column in CANONICAL_PRODUCT_COLUMNS if column not in df.columns]
            if missing:
                raise ConnectorValidationError(f"Connector output missing canonical fields: {missing}")
        return df

    def validate_url(self) -> None:
        if not self.url:
            raise ConnectorValidationError("URL is required")
        parsed = urlparse(self.url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ConnectorValidationError(f"Invalid URL: {self.url}")

    def validate_selector(self, required: bool = False) -> None:
        if required and not self.selector:
            raise ConnectorValidationError("CSS selector is required")
        if self.selector is not None and not str(self.selector).strip():
            raise ConnectorValidationError("CSS selector cannot be blank")

    def validate_file_path(self, path: str | os.PathLike[str] | None) -> None:
        if path is None:
            raise ConnectorValidationError("File path is required")
        if isinstance(path, (str, os.PathLike)) and not os.path.exists(path):
            raise ConnectorValidationError(f"File does not exist: {path}")
