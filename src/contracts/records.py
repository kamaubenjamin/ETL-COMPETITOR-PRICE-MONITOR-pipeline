"""Canonical data records shared by connectors and transformation stages."""

from __future__ import annotations

from datetime import datetime, timezone

CANONICAL_PRODUCT_COLUMNS = [
    "product_name",
    "normalized_name",
    "brand",
    "source",
    "category",
    "current_price",
    "old_price",
    "discount_percentage",
    "currency",
    "availability",
    "sku",
    "url",
    "image_url",
    "timestamp",
    "confidence_score",
]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()