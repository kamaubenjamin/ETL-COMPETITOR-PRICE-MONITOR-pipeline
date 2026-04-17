import pandas as pd
import requests
from bs4 import BeautifulSoup
from src.extract.base_connector import BaseConnector
# ✅ NEW: Added flexible web scraper connector with multiple modes (auto detect, table extraction, full text, custom selector)
class WebScraperConnector(BaseConnector):

    def __init__(self, url, mode="Auto Detect", selector=None):
        self.url = url
        self.mode = mode
        self.selector = selector

    def extract(self):
        response = requests.get(self.url)
        soup = BeautifulSoup(response.text, "html.parser")

        if self.mode == "Auto Detect":
            try:
                tables = pd.read_html(self.url)
                if tables:
                    return tables[0]
            except:
                pass

            text = soup.get_text(" ", strip=True)
            return pd.DataFrame({"content": [text]})

        elif self.mode == "Table Extraction":
            tables = pd.read_html(self.url)
            if not tables:
                raise Exception("No tables found")
            return tables[0]

        elif self.mode == "Full Page Text":
            paragraphs = soup.find_all("p")
            return pd.DataFrame({"content": [p.get_text() for p in paragraphs]})

        elif self.mode == "Custom Selector":
            if not self.selector:
                raise Exception("Selector required")

            elements = soup.select(self.selector)
            return pd.DataFrame({"content": [el.get_text(strip=True) for el in elements]})

        else:
            raise Exception("Invalid mode")