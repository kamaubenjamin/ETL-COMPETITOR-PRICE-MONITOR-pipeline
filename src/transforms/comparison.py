"""Comparison utilities for normalized product intelligence data."""

from __future__ import annotations

import pandas as pd


def compare_same_products(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    working = df.copy()
    key = "normalized_name" if "normalized_name" in working.columns else "product_name"
    if key not in working.columns or "current_price" not in working.columns:
        return pd.DataFrame()

    rows = []
    for product_key, group in working.dropna(subset=[key]).groupby(key):
        priced = group.dropna(subset=["current_price"])
        if priced.empty:
            continue
        cheapest = priced.loc[priced["current_price"].astype(float).idxmin()]
        rows.append(
            {
                "normalized_name": product_key,
                "product_name": cheapest.get("product_name"),
                "cheapest_source": cheapest.get("source"),
                "cheapest_price": cheapest.get("current_price"),
                "source_count": priced["source"].nunique() if "source" in priced.columns else len(priced),
                "price_min": priced["current_price"].astype(float).min(),
                "price_max": priced["current_price"].astype(float).max(),
                "price_variance": priced["current_price"].astype(float).max() - priced["current_price"].astype(float).min(),
                "promotion_detected": bool((priced.get("discount_percentage", pd.Series(dtype=float)).fillna(0) > 0).any()),
            }
        )
    return pd.DataFrame(rows)


def detect_promotions(df: pd.DataFrame, threshold: float = 10) -> pd.DataFrame:
    if df.empty or "discount_percentage" not in df.columns:
        return pd.DataFrame()
    return df[df["discount_percentage"].fillna(0).astype(float) >= threshold].copy()


def detect_undercuts(df: pd.DataFrame, threshold: float = 0) -> pd.DataFrame:
    comparison = compare_same_products(df)
    if comparison.empty:
        return comparison
    return comparison[comparison["price_variance"] > threshold].copy()


def prepare_historical_trends(df: pd.DataFrame) -> pd.DataFrame:
    columns = [col for col in ["timestamp", "normalized_name", "source", "current_price", "availability"] if col in df.columns]
    return df[columns].copy() if columns else pd.DataFrame()
