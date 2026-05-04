import pandas as pd
from rapidfuzz import fuzz

def combine_datasets(datasets: dict) -> pd.DataFrame:
    """
    Combine multiple datasets into one with source labels

    datasets = {
        "jumia": df1,
        "kilimall": df2
    }
    """

    combined = []

    for source, df in datasets.items():
        temp = df.copy()
        temp["source"] = source
        combined.append(temp)

    return pd.concat(combined, ignore_index=True)

# Group similar products based on name similarity

def match_products(df: pd.DataFrame, threshold: int = 70) -> pd.DataFrame:
    """
    Improved product matching using token_set_ratio
    """

    df = df.copy().reset_index(drop=True)
    df["match_id"] = -1

    match_id = 0

    for i in range(len(df)):
        if df.loc[i, "match_id"] != -1:
            continue

        df.loc[i, "match_id"] = match_id
        base_name = df.loc[i, "product_name"]

        for j in range(i + 1, len(df)):
            if df.loc[j, "match_id"] != -1:
                continue

            compare_name = df.loc[j, "product_name"]

            score = fuzz.token_set_ratio(base_name, compare_name)

            if score >= threshold:
                df.loc[j, "match_id"] = match_id

        match_id += 1

    return df