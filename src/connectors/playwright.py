from __future__ import annotations

import pandas as pd
from playwright.sync_api import sync_playwright

from src.connectors.base import BaseConnector


class PlaywrightConnector(BaseConnector):
    def __init__(self, url: str, selector: str | None = None, keyword: str | None = None, **kwargs):
        super().__init__(
            url=url,
            selector=selector,
            keyword=keyword,
            source_type="playwright",
            **kwargs,
        )

    def validate(self) -> None:
        self.validate_url()
        self.validate_selector(required=False)

    def extract(self) -> pd.DataFrame:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(8000)
            target_selector = self.selector or "body"
            elements = page.query_selector_all(target_selector)
            rows = []

            for element in elements:
                try:
                    text = element.inner_text().strip()
                    if not text:
                        continue
                    if self.keyword and self.keyword.lower() not in text.lower():
                        continue
                    rows.append(
                        {
                            "content": text,
                            "source": self.source_name or self.source_type,
                            "url": self.url,
                        }
                    )
                except Exception:
                    continue

            browser.close()

        return pd.DataFrame(rows)
