from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True, slots=True)
class MatchExplanation:
    strategy_used: str
    match_signals: List[str]
    confidence_factors: Dict[str, float]
    fallback_strategies: List[str]
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_used": self.strategy_used,
            "match_signals": self.match_signals,
            "confidence_factors": self.confidence_factors,
            "fallback_strategies": self.fallback_strategies,
            "notes": self.notes,
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)
