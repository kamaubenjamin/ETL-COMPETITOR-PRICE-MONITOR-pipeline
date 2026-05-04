import pandas as pd
import time
import re

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from streamlit import table
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

from src.extract.base_connector import BaseConnector


# SeleniumConnector uses Selenium to scrape data from dynamic web pages.
class SeleniumConnector(BaseConnector):
# It takes a URL, a CSS selector to target specific elements, and an optional keyword for filtering results.
    def __init__(self, url, selector=None, keyword=None):
        super().__init__()  # Call the base class constructor
        self.url = url  # URL of the page to scrape
        self.selector = selector  # CSS selector to find elements
        self.keyword = keyword  # Optional keyword to filter results based on content


# The extract method initializes a headless Chrome browser, navigates to the specified URL,
# and extracts table-like structures dynamically.
    def extract(self):

        if not self.selector or not isinstance(self.selector, str):
            raise Exception("Valid CSS selector is required for Selenium extraction")

        if not self.url:
            raise Exception("URL is required for Selenium extraction")

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")

        # stability improvements
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

        try:
            driver.get(self.url)
            time.sleep(8)

            # -----------------------------
            # GLOBAL ROW DETECTION
            # -----------------------------
            rows = []

            row_elements = driver.find_elements("css selector", "tbody tr")

            if not row_elements:
                row_elements = driver.find_elements("css selector", "tr")

            if not row_elements:
                row_elements = driver.find_elements("css selector", "[role='row']")

            if not row_elements:
                row_elements = driver.find_elements(
                    "css selector",
                    "div[class*='row'], div[class*='Row']"
                )

            if not row_elements:
                raise Exception("No table-like rows found anywhere in DOM")

            # -----------------------------
            # PARSE ROWS
            # -----------------------------
            for row in row_elements:

                text = row.text.strip()

                if not text:
                    continue

                # keyword filter
                if self.keyword:
                    if self.keyword.lower() not in text.lower():
                        continue

                cells = row.find_elements("css selector", "td")

                if cells:
                    row_data = [c.text.strip() for c in cells]
                else:
                    row_data = text.split()

                # -----------------------------
                # FIX: split rank + team
                # -----------------------------
                if row_data and isinstance(row_data[0], str):
                    match = re.match(r"^\d+\s+(.*)", row_data[0])
                    if match:
                        row_data[0] = match.group(1)

                # -----------------------------
                # CLEAN INLINE NOISE (FORM COLUMN)
                # -----------------------------
                row_data = [
                    re.sub(r"\s+", " ", str(cell)).strip()
                    for cell in row_data
                ]

                if row_data:
                    rows.append(row_data)

            if not rows:
                raise Exception("No usable row data extracted")

            # -----------------------------
            # NORMALISE COLUMN WIDTH
            # -----------------------------
            max_cols = max(len(r) for r in rows)

            for row in rows:
                row.extend([""] * (max_cols - len(row)))

            # -----------------------------
            # SMART HEADER DETECTION
            # -----------------------------
            headers = []

            header_elements = driver.find_elements("css selector", "thead th")
            if header_elements:
                headers = [h.text.strip() for h in header_elements if h.text.strip()]

            if not headers:
                header_elements = driver.find_elements("css selector", "[role='columnheader']")
                headers = [h.text.strip() for h in header_elements if h.text.strip()]

            if not headers and len(rows) > 0:
                headers = rows[0]
                rows = rows[1:]

            if not headers:
                headers = [f"Column_{i+1}" for i in range(max_cols)]

            # -----------------------------
            # FOOTBALL SMART HEADER FIX
            # -----------------------------
            football_guess = [
                "Position", "Team", "Played", "Won", "Drawn", "Lost",
                "Goals_For", "Goals_Against", "Goal_Diff", "Points"
            ]

            if all(h.startswith("Column") for h in headers):
                if max_cols >= 9:
                    headers = football_guess[:max_cols]

            # -----------------------------
            # FINAL DATA CLEANING LAYER
            # -----------------------------
            df = pd.DataFrame(rows, columns=headers)

            # remove duplicate whitespace everywhere
            df = df.replace(r"\s+", " ", regex=True)

            # strip strings
            df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

            return df

        finally:
            driver.quit()