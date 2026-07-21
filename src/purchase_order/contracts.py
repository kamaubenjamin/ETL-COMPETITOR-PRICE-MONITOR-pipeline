"""Exact-decimal canonical purchase-order contracts."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import Any


def _decimal(value: Decimal | None) -> str | None:
    return format(value, "f") if value is not None else None


@dataclass(frozen=True, slots=True)
class SourceReference:
    source_type: str
    source_name: str
    ingestion_id: str
    pipeline_run_id: str
    extraction_rule: str = "purchase_order_v1"
    page_count: int | None = None
    line_number: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_name": self.source_name,
            "ingestion_id": self.ingestion_id,
            "pipeline_run_id": self.pipeline_run_id,
            "extraction_rule": self.extraction_rule,
            "page_count": self.page_count,
            "line_number": self.line_number,
        }


@dataclass(frozen=True, slots=True)
class ValidationFinding:
    severity: str
    code: str
    field: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"severity": self.severity, "code": self.code, "field": self.field, "message": self.message}


@dataclass(frozen=True, slots=True)
class PurchaseOrderValidation:
    status: str
    is_valid: bool
    tolerance: Decimal
    findings: tuple[ValidationFinding, ...] = ()
    checks: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "is_valid": self.is_valid,
            "tolerance": _decimal(self.tolerance),
            "findings": [finding.to_dict() for finding in self.findings],
            "checks": dict(self.checks),
        }


@dataclass(frozen=True, slots=True)
class PurchaseOrderLineItem:
    item_code: str | None
    barcode: str | None
    description: str | None
    unit: str | None
    quantity: Decimal | None
    unit_price: Decimal | None
    net_amount: Decimal | None
    source_lineage: SourceReference

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_code": self.item_code,
            "barcode": self.barcode,
            "description": self.description,
            "unit": self.unit,
            "quantity": _decimal(self.quantity),
            "unit_price": _decimal(self.unit_price),
            "net_amount": _decimal(self.net_amount),
            "source_lineage": self.source_lineage.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class PurchaseOrder:
    purchase_order_number: str | None
    buyer: str | None
    supplier: str | None
    ship_to: str | None
    order_date: str | None
    delivery_date: str | None
    currency: str | None
    subtotal: Decimal | None
    tax: Decimal | None
    total: Decimal | None
    line_items: tuple[PurchaseOrderLineItem, ...]
    terms: str | None
    source_lineage: SourceReference
    extraction_warnings: tuple[ValidationFinding, ...] = ()
    validation: PurchaseOrderValidation | None = None
    document_type: str = "purchase_order"

    def with_validation(self, validation: PurchaseOrderValidation) -> "PurchaseOrder":
        return replace(self, validation=validation)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_type": self.document_type,
            "purchase_order_number": self.purchase_order_number,
            "buyer": self.buyer,
            "supplier": self.supplier,
            "ship_to": self.ship_to,
            "order_date": self.order_date,
            "delivery_date": self.delivery_date,
            "currency": self.currency,
            "subtotal": _decimal(self.subtotal),
            "tax": _decimal(self.tax),
            "total": _decimal(self.total),
            "line_items": [item.to_dict() for item in self.line_items],
            "terms": self.terms,
            "source_lineage": self.source_lineage.to_dict(),
            "validation": self.validation.to_dict() if self.validation else None,
            "extraction_warnings": [warning.to_dict() for warning in self.extraction_warnings],
        }
