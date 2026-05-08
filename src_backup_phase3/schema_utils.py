import pandas as pd

def analyze_schema(df: pd.DataFrame):
    return {
        "columns": list(df.columns),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "null_counts": df.isnull().sum().to_dict(),
        "row_count": len(df)
    }

def validate_schema(df, required_columns=None):
    if required_columns is None:
        return True, "No validation required"

    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        return False, f"Missing columns: {missing}"

    return True, "Schema valid"