"""EntitySet — immutable container for all entities extracted from a single document."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List

from src.entity_runtime.contracts.line_item import LineItem
from src.entity_runtime.contracts.supplier import Supplier
from src.entity_runtime.contracts.customer import Customer
from src.entity_runtime.contracts.document_reference import DocumentReference
from src.entity_runtime.contracts.document_financials import DocumentFinancials


@dataclass(frozen=True, slots=True)
class EntitySet:
    """Immutable container for all entities extracted from a single document.

    This is the primary output of the Entity Runtime.
    """

    source_document_id: str
    references: List[DocumentReference] = field(default_factory=list)
    line_items: List[LineItem] = field(default_factory=list)
    suppliers: List[Supplier] = field(default_factory=list)
    customers: List[Customer] = field(default_factory=list)
    financials: List[DocumentFinancials] = field(default_factory=list)
    extraction_metadata: Dict[str, Any] = field(default_factory=dict)
    extraction_confidence: float = 0.0
    created_at: str = ""
    entity_version: int = 0
    """Version number for concurrency hardening. 0 = no versioning (legacy)."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_document_id": self.source_document_id,
            "extraction_confidence": round(float(self.extraction_confidence), 2),
            "entity_version": self.entity_version,
            "entity_counts": {
                "references": len(self.references),
                "line_items": len(self.line_items),
                "suppliers": len(self.suppliers),
                "customers": len(self.customers),
                "financials": len(self.financials),
            },
            "references": [r.to_dict() for r in self.references],
            "line_items": [li.to_dict() for li in self.line_items],
            "suppliers": [s.to_dict() for s in self.suppliers],
            "customers": [c.to_dict() for c in self.customers],
            "financials": [f.to_dict() for f in self.financials],
            "extraction_metadata": self.extraction_metadata,
            "created_at": self.created_at,
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)