# src/extract/base_connector.py

class BaseConnector:
    def __init__(self, config=None, uploaded_df=None, mode=None, selector=None):
        self.config = config
        self.uploaded_df = uploaded_df
        self.mode = mode
        self.selector = selector

    def extract(self):
        raise NotImplementedError("Connector must implement extract()")