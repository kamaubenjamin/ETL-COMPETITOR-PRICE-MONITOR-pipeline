from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from src.review_runtime.models.feedback_record import FeedbackRecord
from src.review_runtime.models.review_correction import ReviewCorrection
from src.review_runtime.models.review_decision import ReviewDecision
from src.review_runtime.models.status import ReviewStatus


@dataclass(frozen=True, slots=True)
class ReviewItem:
    review_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    entity_type: str = ""
    entity_value: str = ""
    confidence: float = 0.0
    status: ReviewStatus = ReviewStatus.PENDING
    created_at: str = ""
    updated_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    decision: Optional[ReviewDecision] = None
    corrections: Tuple[ReviewCorrection, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "review_id": self.review_id,
            "document_id": self.document_id,
            "entity_type": self.entity_type,
            "entity_value": self.entity_value,
            "confidence": round(float(self.confidence), 2),
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "decision": self.decision.to_dict() if self.decision else None,
            "corrections": [correction.to_dict() for correction in self.corrections],
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)
