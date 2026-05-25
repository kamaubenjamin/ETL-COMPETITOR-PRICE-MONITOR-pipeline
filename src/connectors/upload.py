from __future__ import annotations

import pandas as pd

from src.connectors.base import BaseConnector, ConnectorValidationError


class UploadConnector(BaseConnector):
    def __init__(self, dataframe: pd.DataFrame, **kwargs):
        super().__init__(source_type="upload", **kwargs)
        self.dataframe = dataframe

    def validate(self) -> None:
        if self.dataframe is None:
            raise ConnectorValidationError("Uploaded dataframe is required")
        if not isinstance(self.dataframe, pd.DataFrame):
            raise ConnectorValidationError("Uploaded object must be a pandas DataFrame")

    def extract(self) -> pd.DataFrame:
        return self.dataframe.copy()
