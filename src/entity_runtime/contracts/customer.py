"""Customer entity — buyer/customer information from documents."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from src.entity_runtime.contracts.source_lineage import SourceLineage, empty_lineage


@dataclass(frozen=True, slots=True)
class Customer:
    """Customer/buyer information extracted from a document."""

    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: str = "customer"
    confidence: float = 0.5
    source: SourceLineage = field(default_factory=empty_lineage)
    raw_text: str = ""
    name: Optional[str] = None
    address: Optional[str] = None
    contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    customer_id: Optional[str] = None
    tax_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "confidence": round(float(self.confidence), 2),
            "source": self.source.to_dict(),
            "name": self.name,
            "address": self.address,
            "contact": self.contact,
            "email": self.email,
            "phone": self.phone,
            "customer_id": self.customer_id,
            "tax_id": self.tax_id,
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)