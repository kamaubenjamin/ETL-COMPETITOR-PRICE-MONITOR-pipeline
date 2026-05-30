from __future__ import annotations

from typing import Any, Dict

from src.matching_runtime.contracts.match_type import MatchType
from src.matching_runtime.models.match_candidate import MatchCandidate
from src.matching_runtime.models.match_explanation import MatchExplanation
from src.matching_runtime.normalization.text_normalizer import TextNormalizer


class ExactMatchStrategy:
    name = MatchType.EXACT.value

    @staticmethod
    def evaluate(request: "MatchRequest", candidate: MatchCandidate) -> float:
        source_name = TextNormalizer.normalize_text(candidate.candidate_name)
        request_name = TextNormalizer.normalize_text(request.entity_data.get("name", ""))
        return 1.0 if source_name and source_name == request_name else 0.0

    @staticmethod
    def explain(request: "MatchRequest", candidate: MatchCandidate) -> MatchExplanation:
        signals = []
        request_name = request.entity_data.get("name", "")
        candidate_name = candidate.candidate_name
        if request_name and candidate_name and TextNormalizer.normalize_text(request_name) == TextNormalizer.normalize_text(candidate_name):
            signals.append("exact_name")
        return MatchExplanation(
            strategy_used=ExactMatchStrategy.name,
            match_signals=signals,
            confidence_factors={"exact_name": 1.0 if signals else 0.0},
            fallback_strategies=[],
            notes="Exact normalized text comparison.",
        )
