"""Deterministic purchase-order canonicalization public surface."""

from .contracts import (
    PurchaseOrder,
    PurchaseOrderLineItem,
    PurchaseOrderValidation,
    SourceReference,
    ValidationFinding,
)
from .extractor import PurchaseOrderExtractor, classify_purchase_order
from .validator import MONEY_TOLERANCE, validate_purchase_order

__all__ = [
    "MONEY_TOLERANCE",
    "PurchaseOrder",
    "PurchaseOrderExtractor",
    "PurchaseOrderLineItem",
    "PurchaseOrderValidation",
    "SourceReference",
    "ValidationFinding",
    "classify_purchase_order",
    "validate_purchase_order",
]
