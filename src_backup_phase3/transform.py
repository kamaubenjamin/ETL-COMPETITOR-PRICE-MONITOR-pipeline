
from src.utils import log_progress
import pandas as pd
import numpy as np
import pandas.api.types as pd_types
from src.dashboard import uploaded_file 
log_progress("Transform module loaded")


def validate_transform_input(df, required_columns=None):
    if df is None:
        log_progress("Transform skipped: DataFrame is None")
        return pd.DataFrame()

    if df.empty:
        log_progress("Transform skipped: DataFrame is empty")
        return pd.DataFrame()

    if required_columns:
        missing_cols = [col for col in required_columns if col not in df.columns]

        if missing_cols:
            log_progress(f"Warning: Missing required columns: {missing_cols}")
            return False

    return True


def analyze_columns(df):
    analysis = {
        "numeric": [],
        "text": [],
        "datetime": [],
        "boolean": [],
        "others": []
    }

    for col in df.columns:
        dtype = df[col].dtype

        if pd_types.is_numeric_dtype(dtype):
            analysis["numeric"].append(col)

        elif pd_types.is_datetime64_any_dtype(dtype):
            analysis["datetime"].append(col)

        elif pd_types.is_bool_dtype(dtype):
            analysis["boolean"].append(col)

        elif pd_types.is_object_dtype(dtype):
            analysis["text"].append(col)

        else:
            analysis["others"].append(col)

    return analysis


def transform(df, exchange_rate_csv_path=None):
    try:
        log_progress("Starting dynamic transform")

        if df is None or df.empty:
            log_progress("Skipping transform: empty input")
            return df

        df = df.copy()

        column_profile = analyze_columns(df)
        log_progress(f"Detected columns: {column_profile}")

        exchange_rate = {}

        if exchange_rate_csv_path:
            try:
                exchange_df = pd.read_csv(uploaded_file,engine='python',on_bad_lines='skip')
                #st.write("Reading:", config.csv_path)
               

                if exchange_df.shape[1] >= 2:
                    exchange_rate = dict(
                        zip(exchange_df.iloc[:, 0], exchange_df.iloc[:, 1].astype(float))
                    )

            except Exception as e:
                log_progress(f"Exchange rate load failed: {e}")

        if "MC_USD_Billion" in df.columns:

            log_progress("Processing MC_USD_Billion column")

            df["MC_USD_Billion"] = (
                df["MC_USD_Billion"]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.strip()
            )

            df["MC_USD_Billion"] = pd.to_numeric(df["MC_USD_Billion"], errors="coerce")

            df = df.dropna(subset=["MC_USD_Billion"])

            df["MC_USD_Million"] = df["MC_USD_Billion"] * 1000

            for currency in ["GBP", "EUR", "INR"]:
                if currency in exchange_rate:

                    df[f"MC_{currency}_Million"] = np.round(
                        df["MC_USD_Billion"] * exchange_rate[currency] * 1000,
                        2
                    )

        else:
            log_progress("MC_USD_Billion not found → skipping financial transform")

        return df

    except Exception as e:
        log_progress(f"Transform failed: {e}")
        return df