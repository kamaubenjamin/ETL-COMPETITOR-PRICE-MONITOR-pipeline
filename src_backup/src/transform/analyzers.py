import pandas as pd
import pandas.api.types as pd_types

# Analysis functions for DataFrame
def analyze_columns(df: pd.DataFrame):# -> dict: 
    """
    Analyze dataframe column types
    """

    analysis = {
        "numeric": [],
        "text": [],
        "datetime": [],
        "boolean": [],
        "others": []
    }
# Analyze each column type
    for col in df.columns:

        dtype = df[col].dtype

        if pd_types.is_numeric_dtype(dtype):#  is_numeric_dtype checks if the dtype is numeric (int, float, etc.)
            analysis["numeric"].append(col)#  is_datetime64_any_dtype checks if the dtype is any kind of datetime (datetime64, datetime64[ns], etc.)

        elif pd_types.is_datetime64_any_dtype(dtype):
            analysis["datetime"].append(col)

        elif pd_types.is_bool_dtype(dtype):
            analysis["boolean"].append(col)

        elif pd_types.is_object_dtype(dtype):
            analysis["text"].append(col)

        else:
            analysis["others"].append(col)

    return analysis