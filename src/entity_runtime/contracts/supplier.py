"""Supplier entity — vendor/supplier information from documents."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from src.entity_runtime.contracts.source_lineage import SourceLineage, empty_lineage


@dataclass(frozen=True, slots=True)
class Supplier:
    """Supplier/vendor information extracted from a document."""

    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: str = "supplier"
    confidence: float = 0.5
    source: SourceLineage = field(default_factory=empty_lineage)
    raw_text: str = ""
    name: Optional[str] = None
    address: Optional[str] = None
    contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    registration_number: Optional[str] = None
    entity_version: int = 0
    """Version number for concurrency hardening. 0 = no versioning (legacy)."""

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
            "registration_number": self.registration_number,
            "entity_version": self.entity_version,
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)