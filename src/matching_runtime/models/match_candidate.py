from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict

from src.matching_runtime.models.match_explanation import MatchExplanation


@dataclass(frozen=True, slots=True)
class MatchCandidate:
    candidate_id: str
    candidate_name: str
    candidate_fields: Dict[str, Any]
    source: str
    similarity_score: float
    match_explanation: MatchExplanation
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "candidate_name": self.candidate_name,
            "candidate_fields": self.candidate_fields,
            "source": self.source,
            "similarity_score": round(self.similarity_score, 4),
            "confidence": round(self.confidence, 4),
            "match_explanation": self.match_explanation.to_dict(),
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)
