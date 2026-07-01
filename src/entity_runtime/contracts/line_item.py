"""Line item entity — a single product/service line from a document."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from src.entity_runtime.contracts.source_lineage import SourceLineage, empty_lineage


@dataclass(frozen=True, slots=True)
class LineItem:
    """A single product or service line extracted from a document."""

    description: str
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: str = "line_item"
    confidence: float = 0.5
    source: SourceLineage = field(default_factory=empty_lineage)
    raw_text: str = ""
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    unit: Optional[str] = None
    sku: Optional[str] = None
    tax_amount: Optional[float] = None
    discount_amount: Optional[float] = None
    line_number: Optional[int] = None
    entity_version: int = 0
    """Version number for concurrency hardening. 0 = no versioning (legacy)."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "confidence": round(float(self.confidence), 2),
            "source": self.source.to_dict(),
            "description": self.description,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "total_price": self.total_price,
            "unit": self.unit,
            "sku": self.sku,
            "tax_amount": self.tax_amount,
            "discount_amount": self.discount_amount,
            "line_number": self.line_number,
            "entity_version": self.entity_version,
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)