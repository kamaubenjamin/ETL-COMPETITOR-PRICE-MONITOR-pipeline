from src.extract.web_scraper import WebScraperConnector
from src.extract.file_loader import CSVConnector
from src.extract.api_connector import APIConnector
from src.extract.dataframe_connector import dataframe_connector

def get_connector(source_type, config=None, uploaded_df=None, mode=None, selector=None):

    if source_type == "Default (Web)":
        return WebScraperConnector(config.url, mode, selector)

    elif source_type == "CSV":
        return CSVConnector(config.csv_path)

    elif source_type == "Upload Dataset":
        if uploaded_df is None:
            raise ValueError("No uploaded dataframe found")
        return dataframe_connector(uploaded_df)

    elif source_type == "API":
        return APIConnector(config.api_url)

    else:
        raise Exception(f"Unsupported source type: {source_type}")


def run_extraction(source_type, config, uploaded_df=None, mode=None, selector=None):
    connector = get_connector(
        source_type=source_type,
        config=config,
        uploaded_df=uploaded_df,
        mode=mode,
        selector=selector
    )
    return connector.extract()