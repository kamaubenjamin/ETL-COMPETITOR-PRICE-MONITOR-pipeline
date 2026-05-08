import pandas as pd


# -----------------------------
# 🔥 CORE SAFETY FUNCTION
# -----------------------------
def ensure_string_safe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensures all values in the DataFrame are safe strings.
    Prevents .str accessor crashes.
    """
    return df.apply(
        lambda col: col.map(lambda x: str(x) if x is not None else "")
    )


# -----------------------------
# REMOVE DUPLICATES
# -----------------------------
def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop_duplicates()


# -----------------------------
# NORMALIZE COLUMN NAMES
# -----------------------------
def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Ensure column names are strings
    df.columns = df.columns.astype(str)

    # Normalize format
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
    )

    return df


# -----------------------------
# FILL MISSING VALUES
# -----------------------------
def fill_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Replace NaN/None with empty string
    df = df.fillna("")

    # Ensure everything is string-safe
    return ensure_string_safe(df)


# -----------------------------
# TRIM WHITESPACE
# -----------------------------
def trim_whitespace(df: pd.DataFrame) -> pd.DataFrame:
    df = ensure_string_safe(df)

    for col in df.columns:
        df[col] = df[col].str.strip()

    return df
