from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True, slots=True)
class ReviewRequest:
    document_id: str
    entity_type: str
    entity_value: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "entity_type": self.entity_type,
            "entity_value": self.entity_value,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }
