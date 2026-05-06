import pandas as pd
from rapidfuzz import fuzz
from src.transform.product_normalizer import (
    extract_features,
    normalize_name,
    extract_brand,
    detect_category,
)


# -----------------------------
# 🔗 COMBINE DATASETS
# -----------------------------
def combine_datasets(datasets: dict) -> pd.DataFrame:
    combined = []

    for source, df in datasets.items():
        temp = df.copy()
        temp["source"] = source
        combined.append(temp)

    return pd.concat(combined, ignore_index=True)


# -----------------------------
# 🔍 MATCH PRODUCTS
# -----------------------------
def match_products(df: pd.DataFrame, threshold: int = 70) -> pd.DataFrame:
    df = df.copy().reset_index(drop=True)

    if "product_name" not in df.columns:
        raise ValueError("DataFrame must contain a 'product_name' column.")

    if df.empty:
        return df

    df["match_id"] = -1
    df["normalized_name"] = df["product_name"].astype(str).apply(normalize_name)
    features = [extract_features(name) for name in df["product_name"].astype(str)]
    df["feature_brand"] = [f["brand"] for f in features]
    df["feature_size"] = [f["size"] for f in features]
    df["feature_model"] = [f["model"] for f in features]
    df["feature_category"] = [f["category"] for f in features]

    match_id = 0

    for i in range(len(df)):
        if df.loc[i, "match_id"] != -1:
            continue

        df.loc[i, "match_id"] = match_id
        base_norm = df.loc[i, "normalized_name"]
        brand_i = df.loc[i, "feature_brand"]
        size_i = df.loc[i, "feature_size"]
        model_i = df.loc[i, "feature_model"]
        category_i = df.loc[i, "feature_category"]

        for j in range(i + 1, len(df)):
            if df.loc[j, "match_id"] != -1:
                continue

            if category_i != df.loc[j, "feature_category"]:
                continue

            score = 0
            if brand_i and brand_i == df.loc[j, "feature_brand"]:
                score += 30

            if size_i and size_i == df.loc[j, "feature_size"]:
                score += 20

            if model_i and df.loc[j, "feature_model"]:
                if model_i in df.loc[j, "feature_model"] or df.loc[j, "feature_model"] in model_i:
                    score += 20

            fuzzy_score = fuzz.token_set_ratio(base_norm, df.loc[j, "normalized_name"])
            final_score = score + (fuzzy_score * 0.7)

            if final_score >= threshold:
                df.loc[j, "match_id"] = match_id

        match_id += 1

    return df


# -----------------------------
# 💰 BUILD COMPARISON TABLE
# -----------------------------
def build_comparison_table(df: pd.DataFrame) -> pd.DataFrame:
    pivot = df.pivot_table(
        index="match_id",
        columns="source",
        values="price",
        aggfunc="first"
    )

    pivot = pivot.reset_index()

    names = df.groupby("match_id")["product_name"].first().reset_index()

    result = pivot.merge(names, on="match_id")

    # reorder columns
    result = result[
        ["product_name"]
        + [c for c in result.columns if c not in ["product_name", "match_id"]]
    ]

    # -----------------------------
    # 🏆 FIND CHEAPEST
    # -----------------------------
    source_cols = [col for col in result.columns if col != "product_name"]

    def find_cheapest(row):
        prices = {col: row[col] for col in source_cols if pd.notna(row[col])}
        if not prices:
            return None
        return min(prices, key=prices.get)

    result["cheapest"] = result.apply(find_cheapest, axis=1)

    return result