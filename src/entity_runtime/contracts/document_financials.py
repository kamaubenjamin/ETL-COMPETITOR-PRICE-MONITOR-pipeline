"""Document financials entity — financial totals, stripped of header/reference fields."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from src.entity_runtime.contracts.source_lineage import SourceLineage, empty_lineage


@dataclass(frozen=True, slots=True)
class DocumentFinancials:
    """Financial totals extracted from a document.

    Split from DocumentReference to allow clean semantics:
      - Purchase Orders: DocumentReference exists, DocumentFinancials may be empty
      - Invoices: Both DocumentReference and DocumentFinancials present
      - Delivery Notes: DocumentReference exists, DocumentFinancials absent
    """

    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: str = "document_financials"
    confidence: float = 0.5
    source: SourceLineage = field(default_factory=empty_lineage)
    raw_text: str = ""
    subtotal: Optional[float] = None
    tax_total: Optional[float] = None
    discount_total: Optional[float] = None
    grand_total: Optional[float] = None
    line_item_total: Optional[float] = None
    tax_rate: Optional[float] = None
    currency: Optional[str] = None
    net_total: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "confidence": round(float(self.confidence), 2),
            "source": self.source.to_dict(),
            "subtotal": self.subtotal,
            "tax_total": self.tax_total,
            "discount_total": self.discount_total,
            "grand_total": self.grand_total,
            "line_item_total": self.line_item_total,
            "tax_rate": self.tax_rate,
            "currency": self.currency,
            "net_total": self.net_total,
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)