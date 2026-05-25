"""Canonical data records shared by connectors and transformation stages."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd


CANONICAL_PRODUCT_COLUMNS = [
    "product_name",
    "source",
    "category",
    "current_price",
    "old_price",
    "currency",
    "availability",
    "sku",
    "url",
    "timestamp",
]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_product_frame(
    df: pd.DataFrame,
    *,
    source: str | None = None,
    url: str | None = None,
) -> pd.DataFrame:
    """
    Ensure every connector output contains FlowSync's canonical product fields.

    Existing ETL columns are preserved for backward compatibility with the
    product parser, matching engine, and reports.
    """
    normalized = df.copy()
    column_map = {
        "name": "product_name",
        "product": "product_name",
        "title": "product_name",
        "price": "current_price",
        "supplier_price": "current_price",
        "in_stock": "availability",
        "link": "url",
        "product_url": "url",
    }
    for old, new in column_map.items():
        if old in normalized.columns and new not in normalized.columns:
            normalized[new] = normalized[old]

    if "price" not in normalized.columns and "current_price" in normalized.columns:
        normalized["price"] = normalized["current_price"]
    if "product_name" not in normalized.columns and "content" in normalized.columns:
        normalized["product_name"] = normalized["content"].astype(str).str.slice(0, 180)

    defaults: dict[str, Any] = {
        "product_name": None,
        "source": source,
        "category": None,
        "current_price": None,
        "old_price": None,
        "currency": None,
        "availability": None,
        "sku": None,
        "url": url,
        "timestamp": utc_timestamp(),
    }
    for column in CANONICAL_PRODUCT_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = defaults[column]

    return normalized
