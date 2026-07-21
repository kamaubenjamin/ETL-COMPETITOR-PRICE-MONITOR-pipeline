"""Reusable deterministic extraction for machine-readable purchase orders."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
import re
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from src.document_engine.orchestration.ingestion_pipeline import IngestionPipelineResult

from .contracts import PurchaseOrder, PurchaseOrderLineItem, SourceReference, ValidationFinding
from .validator import VALID_CURRENCIES, validate_purchase_order

_PO_MARKERS = ("purchase order", "purchase-order", "po number", "po no", "po #")
_CURRENCIES = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}


def classify_purchase_order(content: str) -> dict[str, object]:
    normalized = " ".join(content.casefold().split())
    marker_count = sum(marker in normalized for marker in _PO_MARKERS)
    supporting = sum(marker in normalized for marker in ("supplier", "ship to", "delivery date", "unit price", "net amount"))
    matched = marker_count >= 1 and supporting >= 2
    confidence = min(0.99, Decimal("0.70") + Decimal("0.05") * (marker_count + supporting)) if matched else Decimal("0.25")
    return {
        "document_type": "purchase_order" if matched else "unknown",
        "confidence": float(confidence),
        "reason": "purchase_order_labels" if matched else "insufficient_purchase_order_signals",
    }


def _amount(value: str | None) -> Decimal | None:
    if value is None:
        return None
    cleaned = re.sub(r"[^0-9().,+-]", "", value).replace(",", "")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    if cleaned in {"", ".", "-", "+"}:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _iso_date(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.strip()
    for pattern in (r"\d{4}-\d{2}-\d{2}", r"\d{2}[/.:-]\d{2}[/.:-]\d{4}", r"\d{1,2}\s+[A-Za-z]{3,9},?\s+\d{4}"):
        match = re.search(pattern, candidate)
        if not match:
            continue
        token = match.group(0)
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %b %Y", "%d %B %Y", "%d %b, %Y", "%d %B, %Y"):
            try:
                return datetime.strptime(token, fmt).date().isoformat()
            except ValueError:
                pass
    return candidate


class PurchaseOrderExtractor:
    """Extract a canonical purchase order from an existing pipeline result."""

    LABELS = {
        "purchase_order_number": ("purchase order number", "purchase order no", "po number", "po no", "po #", "p.o. number", "p.o. no", "order number", "order no"),
        "buyer": ("buyer", "purchaser", "bill to"),
        "supplier": ("supplier", "vendor", "seller"),
        "ship_to": ("ship to", "deliver to", "delivery address"),
        "order_date": ("order date", "po date", "date issued"),
        "delivery_date": ("delivery date", "required date", "deliver by"),
        "terms": ("terms", "payment terms", "delivery terms"),
    }

    def extract(self, pipeline: "IngestionPipelineResult", *, source_name: str = "controlled-local-acceptance") -> PurchaseOrder:
        document = pipeline.ingestion_result.document
        content = document.content
        lines = [line.strip() for line in content.splitlines()]
        lineage = SourceReference(
            source_type=document.source.source_type,
            source_name=source_name,
            ingestion_id=pipeline.ingestion_result.ingestion_id,
            pipeline_run_id=pipeline.pipeline_run_id,
            page_count=document.metadata.get("page_count"),
        )
        warnings: list[ValidationFinding] = []
        if classify_purchase_order(content)["document_type"] != "purchase_order":
            warnings.append(ValidationFinding("warning", "classification_low_confidence", "document_type", "Purchase-order signals were incomplete."))

        fields = {name: self._labeled_value(lines, aliases) for name, aliases in self.LABELS.items()}
        fields["purchase_order_number"] = fields["purchase_order_number"] or self._first_identifier(lines[:18])
        date_candidates = [value for value in (_iso_date(line) for line in lines[:18]) if value and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)]
        normalized_order_date = _iso_date(fields["order_date"])
        normalized_delivery_date = _iso_date(fields["delivery_date"])
        fields["order_date"] = normalized_order_date if normalized_order_date and re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized_order_date) else (date_candidates[0] if date_candidates else None)
        fields["delivery_date"] = normalized_delivery_date if normalized_delivery_date and re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized_delivery_date) else (date_candidates[1] if len(date_candidates) > 1 else None)
        items = self._table_items(pipeline, lineage) or self._vertical_items(lines, lineage)
        subtotal = self._labeled_amount(lines, ("subtotal", "sub total", "net total"))
        tax = self._labeled_amount(lines, ("vat", "tax", "sales tax"))
        total = self._labeled_amount(lines, ("grand total", "order total", "total"), last=True)
        currency = self._currency(content, lines)
        if subtotal is None and items and all(item.net_amount is not None for item in items):
            subtotal = sum((item.net_amount for item in items if item.net_amount is not None), Decimal("0"))
            warnings.append(ValidationFinding("warning", "calculated_from_lines", "subtotal", "Subtotal was calculated from line net amounts."))

        for name in ("buyer", "supplier", "ship_to", "terms"):
            if not fields[name]:
                warnings.append(ValidationFinding("warning", "not_determined", name, f"{name.replace('_', ' ').title()} could not be determined safely."))

        order = PurchaseOrder(
            purchase_order_number=fields["purchase_order_number"],
            buyer=fields["buyer"],
            supplier=fields["supplier"],
            ship_to=fields["ship_to"],
            order_date=_iso_date(fields["order_date"]),
            delivery_date=_iso_date(fields["delivery_date"]),
            currency=currency,
            subtotal=subtotal,
            tax=tax,
            total=total,
            line_items=tuple(items),
            terms=fields["terms"],
            source_lineage=lineage,
            extraction_warnings=tuple(warnings),
        )
        return order.with_validation(validate_purchase_order(order))

    @staticmethod
    def _labeled_value(lines: list[str], aliases: Iterable[str]) -> str | None:
        known_labels = {alias for values in PurchaseOrderExtractor.LABELS.values() for alias in values} | {
            "item code", "barcode", "description", "unit", "quantity", "qty", "unit price", "net amount",
            "subtotal", "sub total", "vat", "tax", "total", "grand total",
        }
        for index, line in enumerate(lines):
            lower = line.casefold().strip().rstrip(":")
            for alias in aliases:
                if lower == alias:
                    return next((candidate for candidate in lines[index + 1:index + 4] if candidate and candidate.casefold().strip().rstrip(":") not in known_labels), None)
                match = re.match(rf"^{re.escape(alias)}\s*(?:[:#-]|\s)\s*(.+)$", line, re.IGNORECASE)
                if match and match.group(1).strip():
                    return match.group(1).strip()
        return None

    @staticmethod
    def _first_identifier(lines: list[str]) -> str | None:
        for line in lines[1:]:
            value = line.strip()
            if re.fullmatch(r"(?=.*\d)[A-Za-z0-9][A-Za-z0-9/_-]{4,}", value):
                return value
        return None

    @staticmethod
    def _labeled_amount(lines: list[str], aliases: Iterable[str], *, last: bool = False) -> Decimal | None:
        matches: list[Decimal] = []
        for index, line in enumerate(lines):
            lower = line.casefold()
            if not any(re.search(rf"\b{re.escape(alias)}\b", lower) for alias in aliases):
                continue
            same_line = _amount(line.split(":", 1)[-1]) if ":" in line else None
            candidate = same_line
            if candidate is None:
                candidate = next((_amount(value) for value in lines[index + 1:index + 3] if _amount(value) is not None), None)
            if candidate is not None:
                matches.append(candidate)
        if not matches:
            return None
        return matches[-1] if last else matches[0]

    @staticmethod
    def _currency(content: str, lines: list[str] | None = None) -> str | None:
        match = re.search(r"\b(USD|EUR|GBP|KES|KSH|TZS|UGX|CAD|AUD|JPY|ZAR)\b", content, re.IGNORECASE)
        if match:
            code = match.group(1).upper()
            return "KES" if code == "KSH" else code
        for line in (lines or [])[:12]:
            candidate = line.strip().upper()
            if candidate in VALID_CURRENCIES:
                return candidate
        symbol = next((symbol for symbol in _CURRENCIES if symbol in content), None)
        return _CURRENCIES.get(symbol) if symbol else None

    def _table_items(self, pipeline: "IngestionPipelineResult", lineage: SourceReference) -> list[PurchaseOrderLineItem]:
        items: list[PurchaseOrderLineItem] = []
        aliases = {
            "item_code": ("item code", "sku", "product code"), "barcode": ("barcode", "ean", "upc"),
            "description": ("description", "item description", "product"), "unit": ("unit", "uom"),
            "quantity": ("quantity", "qty"), "unit_price": ("unit price", "price", "rate"),
            "net_amount": ("net amount", "line total", "amount"),
        }
        for table in pipeline.parsing_result.tables:
            mapping = {field: next((i for i, column in enumerate(table.columns) if any(alias in column.casefold() for alias in names)), None) for field, names in aliases.items()}
            if mapping["description"] is None or mapping["quantity"] is None or mapping["net_amount"] is None:
                continue
            for row_index, row in enumerate(table.rows, 1):
                def value(field: str) -> str | None:
                    pos = mapping[field]
                    return str(row[pos]).strip() if pos is not None and pos < len(row) and row[pos] not in (None, "") else None
                description = value("description")
                if not any(value(field) for field in mapping):
                    continue
                if items and description and not value("quantity") and not value("unit_price") and not value("net_amount"):
                    prior = items.pop()
                    items.append(PurchaseOrderLineItem(prior.item_code, prior.barcode, f"{prior.description or ''} {description}".strip(), prior.unit, prior.quantity, prior.unit_price, prior.net_amount, prior.source_lineage))
                    continue
                items.append(PurchaseOrderLineItem(value("item_code"), value("barcode"), description, value("unit"), _amount(value("quantity")), _amount(value("unit_price")), _amount(value("net_amount")), SourceReference(**{**lineage.to_dict(), "line_number": row_index})))
        return items

    @staticmethod
    def _vertical_items(lines: list[str], lineage: SourceReference) -> list[PurchaseOrderLineItem]:
        header = next((i for i, line in enumerate(lines) if line.casefold() in {"net amount", "line total"}), None)
        if header is None:
            return []
        end = next((i for i in range(header + 1, len(lines)) if lines[i].casefold() in {"subtotal", "sub total", "net total", "grand total", "order total", "total"}), len(lines))
        body = lines[header + 1:end]
        barcode_positions = [i for i, value in enumerate(body) if re.fullmatch(r"\d{8,14}", value)]
        items: list[PurchaseOrderLineItem] = []
        for number, barcode_position in enumerate(barcode_positions):
            start = max(0, barcode_position - 1)
            next_start = max(start + 1, barcode_positions[number + 1] - 1) if number + 1 < len(barcode_positions) else len(body)
            block = [value for value in body[start:next_start] if value]
            if len(block) < 5:
                continue
            decimal_positions = [(i, _amount(value)) for i, value in enumerate(block) if re.fullmatch(r"[-+]?\d[\d,]*\.\d+", value)]
            decimals = [(i, value) for i, value in decimal_positions if value is not None]
            if len(decimals) < 3:
                continue
            quantity_index, quantity = decimals[0]
            unit_price_index, unit_price = decimals[-2]
            net_index, net_amount = decimals[-1]
            unit_index = next((i for i in range(quantity_index - 1, 1, -1) if re.fullmatch(r"[A-Za-z]{1,8}", block[i])), None)
            description_end = unit_index if unit_index is not None else quantity_index
            description = " ".join(block[2:description_end]).strip() or None
            items.append(PurchaseOrderLineItem(block[0], block[1], description, block[unit_index] if unit_index is not None else None, quantity, unit_price, net_amount, SourceReference(**{**lineage.to_dict(), "line_number": header + start + 2})))
        return items
