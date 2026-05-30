from __future__ import annotations

from typing import Dict, List

from src.matching_runtime.contracts.match_request import MatchRequest
from src.matching_runtime.normalization.text_normalizer import TextNormalizer


class InMemoryHistoricalMatchStore:
    def __init__(self) -> None:
        self._history: Dict[str, List[str]] = {}

    @staticmethod
    def _build_history_key(request: MatchRequest) -> str:
        normalized_name = TextNormalizer.normalize_text(request.entity_data.get("name", ""))
        normalized_vendor = TextNormalizer.normalize_text(request.entity_data.get("vendor_code", ""))
        normalized_email = TextNormalizer.normalize_text(request.entity_data.get("email", ""))
        normalized_address = TextNormalizer.normalize_text(request.entity_data.get("address", ""))
        return "|".join(
            [
                request.master_data_type,
                request.entity_type,
                normalized_name,
                normalized_vendor,
                normalized_email,
                normalized_address,
            ]
        )

    def add_match_evidence(self, request: MatchRequest, candidate_id: str) -> None:
        key = self._build_history_key(request)
        values = self._history.setdefault(key, [])
        if candidate_id not in values:
            values.append(candidate_id)

    def get_history_signals(self, request: MatchRequest) -> List[str]:
        key = self._build_history_key(request)
        return list(self._history.get(key, []))
