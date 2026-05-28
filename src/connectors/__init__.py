"""Standard connector architecture for ETL Banking execution plane."""

from src.connectors.base import BaseConnector
from src.connectors.csv import CSVConnector
from src.connectors.playwright import PlaywrightConnector
from src.connectors.smart_playwright import SmartPlaywrightConnector
from src.connectors.upload import UploadConnector
from src.connectors.web import WebConnector

__all__ = [
    "BaseConnector",
    "CSVConnector",
    "PlaywrightConnector",
    "SmartPlaywrightConnector",
    "UploadConnector",
    "WebConnector",
]
