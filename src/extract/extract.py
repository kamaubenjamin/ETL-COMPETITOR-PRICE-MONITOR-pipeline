from src.connectors.web import WebConnector
from src.connectors.csv import CSVConnector
from src.connectors.upload import UploadConnector
from src.connectors.playwright import PlaywrightConnector
from src.extract.api_connector import APIConnector
from src.extract.selenium_connector import SeleniumConnector
from src.extract.internal_connector import InternalDataConnector
# Factory function to get the appropriate connector based on the source type specified by the user.
def get_connector(source_type, config=None, uploaded_df=None, mode=None, selector=None, source_name=None, run_id=None):

    source_type = source_type.strip().lower()   # 🔥 normalize everything
    mode = mode or "Auto Detect"

    if source_type == "default (web)":
        return WebConnector(
            url=config.url,
            mode=mode,
            selector=selector,
            source_name=source_name or source_type,
            run_id=run_id,
        )

    elif source_type == "csv":
        return CSVConnector(
            config.csv_path,
            source_name=source_name or source_type,
            run_id=run_id,
        )

    elif source_type == "upload dataset":
        if uploaded_df is None:
            raise ValueError("No uploaded dataframe found")
        return UploadConnector(
            uploaded_df,
            source_name=source_name or source_type,
            run_id=run_id,
        )

    elif source_type == "api":
        return APIConnector(config.api_url)

    elif source_type == "selenium":
        return SeleniumConnector(
            url=config.url,
            selector=selector,
            keyword=getattr(config, "keyword", None)
        )

    elif source_type == "playwright":
        return PlaywrightConnector(
            url=config.url,
            selector=selector,
            keyword=getattr(config, "keyword", None),
            source_name=source_name or source_type,
            run_id=run_id,
        )

    elif source_type == "internal":
        return InternalDataConnector(
            file_path=config.url,  # Using url field for file path
            source_type=getattr(config, "source_type", "csv")
        )

    else:
        raise Exception(f"Unsupported source type: {repr(source_type)}")


def run_extraction(source_type, config, uploaded_df=None, mode=None, selector=None, source_name=None, run_id=None):
    connector = get_connector(
        source_type=source_type,
        config=config,
        uploaded_df=uploaded_df,
        mode=mode,
        selector=selector,
        source_name=source_name,
        run_id=run_id,
    )
    print("RUNNING WITH SOURCE:", repr(source_type))
    if hasattr(connector, "run"):
        return connector.run()
    return connector.extract()
