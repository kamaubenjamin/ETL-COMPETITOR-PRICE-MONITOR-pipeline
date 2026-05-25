from __future__ import annotations

import pandas as pd

from src.connectors.base import BaseConnector, ConnectorValidationError


class CSVConnector(BaseConnector):
    def __init__(self, file, **kwargs):
        super().__init__(source_type="csv", **kwargs)
        self.file = file

    def validate(self) -> None:
        if self.file is None:
            raise ConnectorValidationError("CSV file is required")
        if isinstance(self.file, str):
            self.validate_file_path(self.file)

    def extract(self) -> pd.DataFrame:
        df = pd.read_csv(self.file, engine="python", on_bad_lines="skip")
        if len(df.columns) == 0:
            raise ConnectorValidationError("CSV has no columns")
        return df
