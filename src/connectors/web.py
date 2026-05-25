from __future__ import annotations

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.connectors.base import BaseConnector, ConnectorValidationError


class WebConnector(BaseConnector):
    def __init__(self, url: str, mode: str = "Auto Detect", selector: str | None = None, **kwargs):
        super().__init__(url=url, mode=mode, selector=selector, source_type="web", **kwargs)

    def validate(self) -> None:
        self.validate_url()
        self.validate_selector(required=self.mode == "Custom Selector")

    def extract(self) -> pd.DataFrame:
        response = requests.get(self.url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        if self.mode == "Auto Detect":
            try:
                tables = pd.read_html(self.url)
                if tables:
                    return tables[0]
            except Exception:
                pass
            return pd.DataFrame({"content": [soup.get_text(" ", strip=True)]})

        if self.mode == "Table Extraction":
            tables = pd.read_html(self.url)
            if not tables:
                raise ConnectorValidationError("No tables found")
            return tables[0]

        if self.mode == "Full Page Text":
            paragraphs = soup.find_all("p")
            return pd.DataFrame({"content": [p.get_text(strip=True) for p in paragraphs]})

        if self.mode == "Custom Selector":
            elements = soup.select(self.selector)
            return pd.DataFrame({"content": [el.get_text(strip=True) for el in elements]})

        raise ConnectorValidationError(f"Invalid web extraction mode: {self.mode}")
