from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True, slots=True)
class ReviewDecision:
    decision: str
    reviewer: str
    timestamp: str
    comment: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "reviewer": self.reviewer,
            "timestamp": self.timestamp,
            "comment": self.comment,
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)
