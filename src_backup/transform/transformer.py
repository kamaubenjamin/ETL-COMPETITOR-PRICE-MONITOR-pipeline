import pandas as pd


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Remove duplicates
    df = df.drop_duplicates()

    # Trim column names
    df.columns = df.columns.str.strip()

    # Handle missing values
    df = df.fillna("")

    return df


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Standardize column names
    df.columns = (
        df.columns.str.lower()
        .str.replace(" ", "_")
        .str.replace("-", "_")
    )

    return df


def transform(df: pd.DataFrame, exchange_rate_csv_path: str = None) -> pd.DataFrame:
    """
    Main transformation pipeline
    """
    df = clean_data(df)
    df = normalize_columns(df)

    return df