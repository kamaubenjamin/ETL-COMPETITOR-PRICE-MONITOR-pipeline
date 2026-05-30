from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.matching_runtime.contracts.match_type import MatchType
from src.matching_runtime.models.match_candidate import MatchCandidate
from src.matching_runtime.models.match_explanation import MatchExplanation


@dataclass(frozen=True, slots=True)
class MatchResult:
    request_id: str
    entity_id: str
    matched: bool
    match_type: MatchType
    best_match: Optional[MatchCandidate]
    all_candidates: List[MatchCandidate]
    overall_confidence: float
    explanation: MatchExplanation
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "entity_id": self.entity_id,
            "matched": self.matched,
            "match_type": self.match_type.value,
            "best_match": self.best_match.to_dict() if self.best_match else None,
            "all_candidates": [candidate.to_dict() for candidate in self.all_candidates],
            "overall_confidence": round(self.overall_confidence, 4),
            "explanation": self.explanation.to_dict(),
            "created_at": self.created_at,
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)
