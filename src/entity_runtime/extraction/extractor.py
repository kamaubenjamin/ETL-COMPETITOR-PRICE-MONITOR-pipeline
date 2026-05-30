"""Deterministic extraction helpers for Entity Runtime v1."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from src.document_engine.orchestration.ingestion_pipeline import IngestionPipelineResult
from src.document_engine.structure.models.canonical_table import CanonicalTable
from src.entity_runtime.contracts import (
    Customer,
    DocumentFinancials,
    DocumentReference,
    LineItem,
    SourceLineage,
    Supplier,
)
from src.entity_runtime.normalization import TextNormalizer


class EntityExtractor:
    """Helper class for extracting entity components from document content."""

    def __init__(self, extraction_rule: str = "entity_runtime_v1"):
        self.extraction_rule = extraction_rule

    def extract_document_references(
        self,
        content: str,
        sections: List[Dict[str, Any]],
        classification: Dict[str, Any],
        lineage: SourceLineage,
    ) -> List[DocumentReference]:
        reference = DocumentReference(
            source=lineage,
            raw_text=content,
            document_type=self._infer_document_type(content, classification),
            document_number=self._extract_field(content, ["invoice number", "invoice #", "inv no"], default=""),
            purchase_order=self._extract_field(content, ["purchase order", "po number", "po #", "order number"], default=""),
            invoice_date=self._extract_field(content, ["invoice date"], default=""),
            due_date=self._extract_field(content, ["due date", "payment due"], default=""),
            currency=self._extract_currency(content),
            payment_terms=self._extract_field(content, ["payment terms", "terms"], default=""),
        )

        return [reference] if self._has_content(reference) else []

    def extract_suppliers(self, content: str, sections: List[Dict[str, Any]], lineage: SourceLineage) -> List[Supplier]:
        section_text = self._section_text(sections, "supplier_section") or content
        supplier = Supplier(
            source=self._build_source_lineage(
                lineage.source_type,
                lineage.source_path,
                lineage.ingestion_id,
                lineage.pipeline_run_id,
                line_number=self._section_start_line(sections, "supplier_section"),
            ),
            raw_text=section_text,
            name=self._extract_field(section_text, ["supplier", "vendor", "sold by", "seller", "bill from", "from"], default=""),
            address=self._extract_address(section_text),
            email=self._extract_email(section_text),
            phone=self._extract_phone(section_text),
        )
        return [supplier] if self._has_content(supplier) else []

    def extract_customers(self, content: str, sections: List[Dict[str, Any]], lineage: SourceLineage) -> List[Customer]:
        section_text = self._section_text(sections, "customer_section") or content
        customer = Customer(
            source=self._build_source_lineage(
                lineage.source_type,
                lineage.source_path,
                lineage.ingestion_id,
                lineage.pipeline_run_id,
                line_number=self._section_start_line(sections, "customer_section"),
            ),
            raw_text=section_text,
            name=self._extract_field(section_text, ["customer", "buyer", "bill to", "ship to", "recipient", "purchaser"], default=""),
            address=self._extract_address(section_text),
            email=self._extract_email(section_text),
            phone=self._extract_phone(section_text),
        )
        return [customer] if self._has_content(customer) else []

    def extract_financials(
        self,
        content: str,
        sections: List[Dict[str, Any]],
        tables: List[CanonicalTable],
        lineage: SourceLineage,
    ) -> List[DocumentFinancials]:
        totals_text = self._section_text(sections, "totals_section") or content
        financials = DocumentFinancials(
            source=self._build_source_lineage(
                lineage.source_type,
                lineage.source_path,
                lineage.ingestion_id,
                lineage.pipeline_run_id,
                line_number=self._section_start_line(sections, "totals_section"),
            ),
            raw_text=totals_text,
            subtotal=self._extract_amount(totals_text, ["subtotal"]),
            tax_total=self._extract_amount(totals_text, ["tax", "vat", "sales tax"]),
            discount_total=self._extract_amount(totals_text, ["discount"]),
            grand_total=self._extract_amount(totals_text, ["grand total", "amount due", "total", "balance"]),
            net_total=self._extract_amount(totals_text, ["net total", "amount due", "balance"]),
            currency=self._extract_currency(totals_text),
        )
        return [financials] if self._has_content(financials) else []

    def extract_line_items(
        self,
        content: str,
        sections: List[Dict[str, Any]],
        tables: List[CanonicalTable],
        lineage: SourceLineage,
    ) -> List[LineItem]:
        items: List[LineItem] = []

        for table_index, table in enumerate(tables):
            column_map = self._map_table_columns(table.columns)
            for row_index, row in enumerate(table.rows):
                line_item = self._row_to_line_item(row, column_map, lineage, row_index, table.confidence_score)
                if line_item is not None:
                    items.append(line_item)

        if not items:
            section_text = self._section_text(sections, "line_items_section")
            if section_text:
                items.extend(self._parse_line_items_from_text(section_text, lineage))

        return items

    def _build_source_lineage(
        self,
        source_type: str,
        source_path: str,
        ingestion_id: str,
        pipeline_run_id: str,
        parsed_block_index: int = -1,
        line_number: Optional[int] = None,
    ) -> SourceLineage:
        return SourceLineage(
            source_type=source_type,
            source_path=source_path,
            ingestion_id=ingestion_id,
            pipeline_run_id=pipeline_run_id,
            parsed_block_index=parsed_block_index,
            line_number=line_number,
            extraction_rule=self.extraction_rule,
        )

    def _map_table_columns(self, columns: List[str]) -> Dict[str, int]:
        mapping: Dict[str, int] = {}
        for index, column in enumerate(columns):
            normalized = column.strip().lower()
            if any(token in normalized for token in ["description", "item", "product", "name"]):
                mapping.setdefault("description", index)
            if any(token in normalized for token in ["qty", "quantity", "qty.", "quant"]):
                mapping.setdefault("quantity", index)
            if any(token in normalized for token in ["unit price", "unit_cost", "price", "rate", "cost"]):
                mapping.setdefault("unit_price", index)
            if any(token in normalized for token in ["line total", "total", "amount", "price"]):
                mapping.setdefault("total_price", index)
            if any(token in normalized for token in ["sku", "product code", "item code", "part number"]):
                mapping.setdefault("sku", index)
        return mapping

    def _row_to_line_item(
        self,
        row: List[Optional[str]],
        column_map: Dict[str, int],
        lineage: SourceLineage,
        row_index: int,
        table_confidence: float,
    ) -> Optional[LineItem]:
        row_values = [str(cell).strip() if cell is not None else "" for cell in row]
        description = self._select_first(row_values, column_map.get("description"))
        quantity = self._parse_raw_amount(self._select_first(row_values, column_map.get("quantity")))
        unit_price = self._parse_raw_amount(self._select_first(row_values, column_map.get("unit_price")))
        total_price = self._parse_raw_amount(self._select_first(row_values, column_map.get("total_price")))
        sku = self._select_first(row_values, column_map.get("sku"))

        if not any([description, quantity, unit_price, total_price, sku]):
            return None

        confidence = round(min(max(float(table_confidence or 0.5), 0.2), 0.95), 2)
        return LineItem(
            source=self._build_source_lineage(
                lineage.source_type,
                lineage.source_path,
                lineage.ingestion_id,
                lineage.pipeline_run_id,
                line_number=row_index + 1,
            ),
            raw_text=" | ".join(row_values),
            description=description,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price,
            sku=sku,
            confidence=confidence,
        )

    def _parse_line_items_from_text(self, content: str, lineage: SourceLineage) -> List[LineItem]:
        items: List[LineItem] = []
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        for line_number, line in enumerate(lines, start=1):
            numeric_values = [self._parse_raw_amount(token) for token in re.findall(r"[-+]?\d[\d,]*\.?\d+", line)]
            if len(numeric_values) < 1 or len(line.split()) < 2:
                continue
            description = re.sub(r"\s{2,}|\t", " ", line).strip()
            quantity = numeric_values[0] if len(numeric_values) >= 1 else None
            total_price = numeric_values[-1] if len(numeric_values) >= 1 else None
            items.append(
                LineItem(
                    source=self._build_source_lineage(
                        lineage.source_type,
                        lineage.source_path,
                        lineage.ingestion_id,
                        lineage.pipeline_run_id,
                        line_number=line_number,
                    ),
                    raw_text=line,
                    description=description,
                    quantity=quantity,
                    total_price=total_price,
                    confidence=0.5,
                )
            )
        return items

    def _section_text(self, sections: List[Dict[str, Any]], section_type: str) -> Optional[str]:
        for section in sections:
            if section.get("section_type") == section_type:
                return section.get("content")
        return None

    def _section_start_line(self, sections: List[Dict[str, Any]], section_type: str) -> Optional[int]:
        for section in sections:
            if section.get("section_type") == section_type:
                return section.get("start_line")
        return None

    def _extract_field(self, content: str, labels: List[str], default: str = "") -> str:
        for line in content.splitlines():
            normalized = TextNormalizer.normalize_whitespace(line).lower()
            for label in labels:
                if label in normalized:
                    parts = re.split(r":|#|\s+\-\s+", line, maxsplit=1)
                    if len(parts) > 1 and parts[1].strip():
                        return parts[1].strip()
                    return line.strip()
        return default

    def _extract_address(self, content: str) -> str:
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        for line in lines:
            if any(token in line.lower() for token in ["address", "addr", "street", "road", "ave", "blvd", "suite"]):
                return line.strip()
        return lines[0] if lines else ""

    def _extract_email(self, content: str) -> str:
        match = re.search(r"[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}", content)
        return match.group(0) if match else ""

    def _extract_phone(self, content: str) -> str:
        match = re.search(r"\+?\d[\d\s\-\(\)]{6,}\d", content)
        return match.group(0).strip() if match else ""

    def _extract_amount(self, content: str, labels: List[str]) -> Optional[float]:
        for line in content.splitlines():
            normalized = TextNormalizer.normalize_whitespace(line).lower()
            for label in labels:
                if re.search(rf"\b{re.escape(label)}\b", normalized):
                    amount = self._parse_raw_amount(line)
                    if amount is not None:
                        return amount
        if labels:
            for token in re.findall(r"[-+]?\d[\d,]*\.?\d+", content):
                amount = self._parse_raw_amount(token)
                if amount is not None:
                    return amount
        return None

    def _parse_raw_amount(self, raw_value: str) -> Optional[float]:
        if raw_value is None:
            return None
        text = str(raw_value)
        cleaned = re.sub(r"[^0-9\.-]", "", text)
        if cleaned in {"", ".", "-", "--"}:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _extract_currency(self, content: str) -> Optional[str]:
        match = re.search(r"\b(USD|EUR|GBP|NGN|KES|TZS|UGX|CAD|AUD|JPY)\b", content, re.IGNORECASE)
        if match:
            return match.group(0).upper()
        symbol_match = re.search(r"(\$|€|£|¥)", content)
        if symbol_match:
            symbol = symbol_match.group(0)
            return {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}.get(symbol)
        return None

    def _infer_document_type(self, content: str, classification: Dict[str, Any]) -> Optional[str]:
        if classification and classification.get("document_type"):
            return str(classification["document_type"])
        normalized = content.lower()
        if "invoice" in normalized:
            return "invoice"
        if "purchase order" in normalized or "po number" in normalized:
            return "purchase_order"
        if "delivery note" in normalized:
            return "delivery_note"
        if "receipt" in normalized:
            return "receipt"
        return None

    def _select_first(self, values: List[str], index: Optional[int]) -> str:
        if index is None or index < 0 or index >= len(values):
            return ""
        return values[index]

    def _has_content(self, entity: Any) -> bool:
        payload = entity.to_dict()
        for key, value in payload.items():
            if key in {"entity_id", "entity_type", "confidence", "source"}:
                continue
            if value not in (None, "", [], {}):
                return True
        return False
