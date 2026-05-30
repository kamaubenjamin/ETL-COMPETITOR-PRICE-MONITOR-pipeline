from __future__ import annotations

from typing import Any, Dict

from src.matching_runtime.contracts.match_type import MatchType
from src.matching_runtime.models.match_candidate import MatchCandidate
from src.matching_runtime.models.match_explanation import MatchExplanation
from src.matching_runtime.normalization.text_normalizer import TextNormalizer


class NormalizedMatchStrategy:
    name = MatchType.NORMALIZED.value

    @staticmethod
    def evaluate(request: "MatchRequest", candidate: MatchCandidate) -> float:
        request_name = request.entity_data.get("name", "")
        candidate_name = candidate.candidate_name
        if TextNormalizer.compare_normalized(request_name, candidate_name):
            return 0.95
        return 0.0

    @staticmethod
    def explain(request: "MatchRequest", candidate: MatchCandidate) -> MatchExplanation:
        signals = []
        if TextNormalizer.compare_normalized(request.entity_data.get("name", ""), candidate.candidate_name):
            signals.append("normalized_name")
        return MatchExplanation(
            strategy_used=NormalizedMatchStrategy.name,
            match_signals=signals,
            confidence_factors={"normalized_name": 0.95 if signals else 0.0},
            fallback_strategies=[ExactMatchStrategy.name],
            notes="Normalized name match after text normalization.",
        )


# avoid circular import in type hints
from src.matching_runtime.strategies.exact_match_strategy import ExactMatchStrategy
