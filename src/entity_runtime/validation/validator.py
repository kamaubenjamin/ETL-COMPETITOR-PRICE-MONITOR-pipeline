"""Validation helpers for Entity Runtime v1."""

from __future__ import annotations

from typing import Any, Dict, List

from src.entity_runtime.contracts import EntitySet


class EntityValidator:
    """Validates extracted entities and returns a lightweight result payload."""

    def validate(self, entity_set: EntitySet) -> Dict[str, Any]:
        issues: List[str] = []

        if not any([entity_set.references, entity_set.financials, entity_set.line_items, entity_set.suppliers, entity_set.customers]):
            issues.append("no_entities_extracted")

        if entity_set.references:
            reference = entity_set.references[0]
            if not reference.document_number and not reference.purchase_order:
                issues.append("missing_document_reference_number")

        if entity_set.financials:
            financials = entity_set.financials[0]
            if financials.grand_total is None and financials.subtotal is None:
                issues.append("missing_financial_totals")

        if entity_set.line_items:
            for index, item in enumerate(entity_set.line_items, start=1):
                if item.total_price is None and item.quantity is None:
                    issues.append(f"line_item_{index}_missing_numeric_values")

        return {
            "entity_validation_passed": len(issues) == 0,
            "entity_validation_issues": issues,
        }
