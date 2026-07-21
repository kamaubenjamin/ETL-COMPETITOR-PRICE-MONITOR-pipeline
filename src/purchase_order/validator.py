"""Deterministic purchase-order business validation."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from .contracts import PurchaseOrder, PurchaseOrderValidation, ValidationFinding

MONEY_TOLERANCE = Decimal("0.01")
VALID_CURRENCIES = frozenset({
    "AED", "AUD", "BRL", "CAD", "CHF", "CNY", "DKK", "EGP", "EUR", "GBP", "GHS", "INR", "JPY",
    "KES", "MAD", "MUR", "NGN", "NOK", "NZD", "RWF", "SAR", "SEK", "SGD", "TZS", "UGX", "USD",
    "XAF", "XOF", "ZAR", "ZMW",
})


def _date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def validate_purchase_order(order: PurchaseOrder, tolerance: Decimal = MONEY_TOLERANCE) -> PurchaseOrderValidation:
    findings: list[ValidationFinding] = []
    checks: dict[str, bool] = {}

    def check(name: str, passed: bool, field: str, code: str, message: str, severity: str = "error") -> None:
        checks[name] = passed
        if not passed:
            findings.append(ValidationFinding(severity, code, field, message))

    check("purchase_order_number_present", bool(order.purchase_order_number), "purchase_order_number", "required", "Purchase-order number is required.")
    order_date = _date(order.order_date)
    delivery_date = _date(order.delivery_date)
    check("order_date_valid", order_date is not None, "order_date", "invalid_date", "Order date is missing or invalid.")
    check("delivery_date_valid", delivery_date is not None, "delivery_date", "invalid_date", "Delivery date is missing or invalid.")
    chronology_ok = order_date is None or delivery_date is None or delivery_date >= order_date
    check("delivery_not_before_order", chronology_ok, "delivery_date", "date_order", "Delivery date cannot precede order date.")
    check("line_items_present", bool(order.line_items), "line_items", "required", "At least one line item is required.")

    codes: list[str] = []
    line_amounts: list[Decimal] = []
    for index, item in enumerate(order.line_items):
        prefix = f"line_items[{index}]"
        check(f"{prefix}.quantity_positive", item.quantity is not None and item.quantity > 0, f"{prefix}.quantity", "invalid_quantity", "Quantity must be positive.")
        check(f"{prefix}.unit_price_non_negative", item.unit_price is not None and item.unit_price >= 0, f"{prefix}.unit_price", "invalid_unit_price", "Unit price must be non-negative.")
        arithmetic_ok = (
            item.quantity is not None and item.unit_price is not None and item.net_amount is not None
            and abs((item.quantity * item.unit_price) - item.net_amount) <= tolerance
        )
        check(f"{prefix}.amount_matches", arithmetic_ok, f"{prefix}.net_amount", "line_amount_mismatch", "Quantity multiplied by unit price does not match net amount.")
        if item.net_amount is not None:
            line_amounts.append(item.net_amount)
        if item.item_code:
            codes.append(item.item_code.casefold())

    duplicates = sorted({code for code in codes if codes.count(code) > 1})
    check("item_codes_unique", not duplicates, "line_items.item_code", "duplicate_item_code", "Duplicate item codes were found.", "warning")
    subtotal_ok = order.subtotal is not None and bool(line_amounts) and abs(sum(line_amounts, Decimal("0")) - order.subtotal) <= tolerance
    check("subtotal_matches_lines", subtotal_ok, "subtotal", "subtotal_mismatch", "Line net amounts do not reconcile to subtotal.")
    total_ok = order.subtotal is not None and order.tax is not None and order.total is not None and abs((order.subtotal + order.tax) - order.total) <= tolerance
    check("total_matches_subtotal_and_tax", total_ok, "total", "total_mismatch", "Subtotal plus tax does not reconcile to total.")
    check("currency_valid", order.currency in VALID_CURRENCIES, "currency", "invalid_currency", "Currency is missing or unsupported.")

    is_valid = not any(finding.severity == "error" for finding in findings)
    status = "valid" if not findings else "valid_with_warnings" if is_valid else "invalid"
    return PurchaseOrderValidation(status, is_valid, tolerance, tuple(findings), checks)
