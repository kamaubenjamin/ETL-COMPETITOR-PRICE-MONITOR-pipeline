from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True, slots=True)
class ReviewCorrection:
    original_value: str
    corrected_value: str
    reason: str
    reviewer: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_value": self.original_value,
            "corrected_value": self.corrected_value,
            "reason": self.reason,
            "reviewer": self.reviewer,
            "timestamp": self.timestamp,
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)
