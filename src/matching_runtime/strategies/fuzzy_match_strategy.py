from __future__ import annotations

import difflib
from typing import Any

from src.matching_runtime.contracts.match_type import MatchType
from src.matching_runtime.models.match_candidate import MatchCandidate
from src.matching_runtime.models.match_explanation import MatchExplanation
from src.matching_runtime.normalization.text_normalizer import TextNormalizer


class FuzzyMatchStrategy:
    name = MatchType.FUZZY.value
    threshold = 0.75
    base_confidence = 0.8
    scaling_factor = 0.3

    @staticmethod
    def similarity_score(source: str, target: str) -> float:
        if not source or not target:
            return 0.0
        normalized_source = TextNormalizer.normalize_text(source)
        normalized_target = TextNormalizer.normalize_text(target)
        return difflib.SequenceMatcher(None, normalized_source, normalized_target).ratio()

    @staticmethod
    def evaluate(request: "MatchRequest", candidate: MatchCandidate) -> float:
        score = FuzzyMatchStrategy.similarity_score(request.entity_data.get("name", ""), candidate.candidate_name)
        if score < FuzzyMatchStrategy.threshold:
            return 0.0
        return min(1.0, FuzzyMatchStrategy.base_confidence + (score - FuzzyMatchStrategy.threshold) * FuzzyMatchStrategy.scaling_factor)

    @staticmethod
    def explain(request: "MatchRequest", candidate: MatchCandidate) -> MatchExplanation:
        score = FuzzyMatchStrategy.similarity_score(request.entity_data.get("name", ""), candidate.candidate_name)
        signals = []
        if score >= FuzzyMatchStrategy.threshold:
            signals.append("fuzzy_name")
        return MatchExplanation(
            strategy_used=FuzzyMatchStrategy.name,
            match_signals=signals,
            confidence_factors={
                "name_similarity": score,
                "threshold": FuzzyMatchStrategy.threshold,
            },
            fallback_strategies=[ExactMatchStrategy.name, NormalizedMatchStrategy.name],
            notes="Fuzzy similarity match used for lossy string differences.",
        )


from src.matching_runtime.strategies.exact_match_strategy import ExactMatchStrategy
from src.matching_runtime.strategies.normalized_match_strategy import NormalizedMatchStrategy
