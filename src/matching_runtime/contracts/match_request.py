from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True, slots=True)
class MatchRequest:
    request_id: str
    entity_id: str
    entity_type: str
    entity_data: Dict[str, Any]
    master_data_type: str
    match_strategy: str = "default"
    confidence_threshold: float = 0.7
    allow_multiple_matches: bool = False
    source_lineage: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "entity_data": self.entity_data,
            "master_data_type": self.master_data_type,
            "match_strategy": self.match_strategy,
            "confidence_threshold": self.confidence_threshold,
            "allow_multiple_matches": self.allow_multiple_matches,
            "source_lineage": self.source_lineage,
            "metadata": self.metadata,
        }

    def to_json(self, **kwargs: Any) -> str:
        import json

        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)
