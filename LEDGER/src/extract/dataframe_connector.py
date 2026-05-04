import pandas as pd
from src.extract.base_connector import BaseConnector

class DataFrameConnector(BaseConnector):

    def __init__(self, df):
        super().__init__()
        self.df = df

    def extract(self):
        if self.df is None:
            raise ValueError("DataFrameConnector received None dataframe")

        return self.df.copy()