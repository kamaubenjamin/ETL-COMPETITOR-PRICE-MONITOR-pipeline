import pandas as pd
from src.extract.base_connector import BaseConnector

class CSVConnector:
    def __init__(self, file):
        self.file = file

    def extract(self):
        if self.file is None:
            raise ValueError("CSVConnector received None file path")

        # Streamlit UploadedFile OR file path
        return pd.read_csv(self.file, engine="python", on_bad_lines="skip")