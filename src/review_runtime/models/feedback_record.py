from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from src.review_runtime.models.review_correction import ReviewCorrection
from src.review_runtime.models.review_decision import ReviewDecision


@dataclass(frozen=True, slots=True)
class FeedbackRecord:
    review_id: str
    outcome: str
    review_item: Dict[str, Any]
    decision: Optional[ReviewDecision] = None
    correction: Optional[ReviewCorrection] = None
    created_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "review_id": self.review_id,
            "outcome": self.outcome,
            "review_item": self.review_item,
            "decision": self.decision.to_dict() if self.decision else None,
            "correction": self.correction.to_dict() if self.correction else None,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)
