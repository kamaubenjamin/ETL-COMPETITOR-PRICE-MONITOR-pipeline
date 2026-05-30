from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List

from src.matching_runtime.models.match_result import MatchResult


@dataclass(frozen=True, slots=True)
class MatchSet:
    source_document_id: str
    matches: List[MatchResult]
    match_statistics: Dict[str, Any]
    overall_confidence: float
    matching_metadata: Dict[str, Any]
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_document_id": self.source_document_id,
            "matches": [match.to_dict() for match in self.matches],
            "match_statistics": self.match_statistics,
            "overall_confidence": round(self.overall_confidence, 4),
            "matching_metadata": self.matching_metadata,
            "created_at": self.created_at,
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)
