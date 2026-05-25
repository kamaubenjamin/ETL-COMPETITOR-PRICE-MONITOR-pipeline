import pandas as pd

from src.connectors.upload import UploadConnector
from src.contracts.records import CANONICAL_PRODUCT_COLUMNS


def test_upload_connector_normalizes_to_canonical_schema():
    df = pd.DataFrame(
        {
            "name": ["Phone A"],
            "price": [1000],
            "availability": ["available"],
        }
    )

    result = UploadConnector(df, source_name="unit_test").run()

    for column in CANONICAL_PRODUCT_COLUMNS:
        assert column in result.columns
    assert result.iloc[0]["product_name"] == "Phone A"
    assert result.iloc[0]["current_price"] == 1000
    assert result.iloc[0]["source"] == "unit_test"
