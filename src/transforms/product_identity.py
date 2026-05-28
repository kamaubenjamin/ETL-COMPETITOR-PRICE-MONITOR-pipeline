"""Product normalization utilities for comparison-ready supermarket data."""

from __future__ import annotations

import re
from typing import Any, Optional

import pandas as pd

from src.contracts.records import (
    CANONICAL_PRODUCT_COLUMNS,
    utc_timestamp,
)

BRAND_VARIANTS = {
    "omo": ["omo"],
    "ariel": ["ariel"],
    "sunlight": ["sunlight"],
    "toss": ["toss"],
    "geisha": ["geisha"],
}

UNIT_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s?(kg|kgs|g|gram|grams|l|ltr|litre|liter|ml|pcs|pieces|pack|sachets?)\b",
    re.IGNORECASE,
)

WHITESPACE_RE = re.compile(r"\s+")


def clean_whitespace(value: str | None) -> str:
    return WHITESPACE_RE.sub(" ", str(value or "")).strip()


def normalize_unit(value: str | None) -> Optional[str]:
    if not value:
        return None

    match = UNIT_RE.search(value)

    if not match:
        return None

    amount = match.group(1).rstrip("0").rstrip(".")
    unit = match.group(2).lower()

    unit = {
        "kgs": "kg",
        "gram": "g",
        "grams": "g",
        "ltr": "l",
        "litre": "l",
        "liter": "l",
        "pieces": "pcs",
        "sachets": "sachet",
    }.get(unit, unit)

    return f"{amount}{unit}"


def normalize_brand(value: str | None) -> Optional[str]:
    normalized = clean_whitespace(value).lower()

    for canonical, variants in BRAND_VARIANTS.items():
        if any(
            re.search(rf"\b{re.escape(variant)}\b", normalized)
            for variant in variants
        ):
            return canonical

    first = normalized.split()[0] if normalized.split() else None

    return first


def normalize_product_name(value: str | None) -> str:
    text = clean_whitespace(value).lower()

    text = re.sub(r"[^a-z0-9\s\.]", " ", text)
    text = WHITESPACE_RE.sub(" ", text)

    unit = normalize_unit(text)
    brand = normalize_brand(text)

    tokens = [
        token
        for token in text.split()
        if token not in {
            "washing",
            "powder",
            "detergent",
            "bar",
            "soap",
        }
    ]

    collapsed = " ".join(dict.fromkeys(tokens))

    if brand and unit:
        return f"{brand} {unit}"

    return collapsed.strip()


def extract_size(value: str | None) -> Optional[str]:
    return normalize_unit(value)


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

    if (
        "price" not in normalized.columns
        and "current_price" in normalized.columns
    ):
        normalized["price"] = normalized["current_price"]

    if (
        "product_name" not in normalized.columns
        and "content" in normalized.columns
    ):
        normalized["product_name"] = (
            normalized["content"]
            .astype(str)
            .str.slice(0, 180)
        )

    defaults: dict[str, Any] = {
        "product_name": None,
        "normalized_name": None,
        "brand": None,
        "source": source,
        "category": None,
        "current_price": None,
        "old_price": None,
        "discount_percentage": None,
        "currency": None,
        "availability": None,
        "sku": None,
        "url": url,
        "image_url": None,
        "timestamp": utc_timestamp(),
        "confidence_score": None,
    }

    for column in CANONICAL_PRODUCT_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = defaults[column]

    if (
        normalized["normalized_name"].isna().all()
        and "product_name" in normalized.columns
    ):
        normalized["normalized_name"] = (
            normalized["product_name"]
            .apply(normalize_product_name)
        )

    if (
        normalized["brand"].isna().all()
        and "product_name" in normalized.columns
    ):
        normalized["brand"] = (
            normalized["product_name"]
            .apply(normalize_brand)
        )

    return normalized


def enrich_product_identity(
    df: pd.DataFrame,
    category: str | None = None,
) -> pd.DataFrame:
    enriched = df.copy()

    if "product_name" in enriched.columns:
        enriched["normalized_name"] = (
            enriched["product_name"]
            .apply(normalize_product_name)
        )

        enriched["brand"] = (
            enriched["product_name"]
            .apply(normalize_brand)
        )

        enriched["size"] = (
            enriched["product_name"]
            .apply(extract_size)
        )

    if category and "category" in enriched.columns:
        enriched["category"] = enriched["category"].fillna(category)

    elif category:
        enriched["category"] = category

    return collapse_duplicates(enriched)


def collapse_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "normalized_name" not in df.columns:
        return df

    sort_cols = [
        col
        for col in ["confidence_score", "current_price"]
        if col in df.columns
    ]

    if sort_cols:
        df = df.sort_values(
            sort_cols,
            ascending=[False] * len(sort_cols),
        )

    subset = [
        col
        for col in [
            "normalized_name",
            "source",
            "current_price",
        ]
        if col in df.columns
    ]

    return df.drop_duplicates(
        subset=subset or None
    ).reset_index(drop=True)