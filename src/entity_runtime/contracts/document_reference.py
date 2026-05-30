"""Document reference entity — header/reference information separate from financial totals."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from src.entity_runtime.contracts.source_lineage import SourceLineage, empty_lineage


@dataclass(frozen=True, slots=True)
class DocumentReference:
    """Document header/reference information extracted from a document.

    Exists independently of financial totals — a Purchase Order may have
    reference numbers but zero financial fields. Split from DocumentFinancials
    to allow clean semantics for POs, Delivery Notes, Credit Notes, etc.
    """

    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: str = "document_reference"
    confidence: float = 0.5
    source: SourceLineage = field(default_factory=empty_lineage)
    raw_text: str = ""
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    invoice_number: Optional[str] = None
    purchase_order: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    payment_terms: Optional[str] = None
    currency: Optional[str] = None
    document_status: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "confidence": round(float(self.confidence), 2),
            "source": self.source.to_dict(),
            "document_type": self.document_type,
            "document_number": self.document_number,
            "invoice_number": self.invoice_number,
            "purchase_order": self.purchase_order,
            "invoice_date": self.invoice_date,
            "due_date": self.due_date,
            "payment_terms": self.payment_terms,
            "currency": self.currency,
            "document_status": self.document_status,
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)