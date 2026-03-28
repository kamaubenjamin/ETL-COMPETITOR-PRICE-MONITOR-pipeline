from src.extract import extract

def test_extract_real_website():
    url = "https://web.archive.org/web/20230908091635/https://en.wikipedia.org/wiki/List_of_largest_banks"
    table_attribs = ["Name", "MC_USD_Billion"]

    df = extract(url, table_attribs)

    # Basic checks using real data
    assert df is not None
    assert len(df) > 0
    assert list(df.columns) == table_attribs

    # Optional: check some expected values exist
    assert "JPMorgan Chase" in df["Name"].values