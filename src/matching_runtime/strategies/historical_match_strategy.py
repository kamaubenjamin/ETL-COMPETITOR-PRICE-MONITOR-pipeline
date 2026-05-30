from __future__ import annotations

from typing import Any, List

from src.matching_runtime.contracts.match_type import MatchType
from src.matching_runtime.models.match_candidate import MatchCandidate
from src.matching_runtime.models.match_explanation import MatchExplanation
from src.matching_runtime.normalization.text_normalizer import TextNormalizer


class HistoricalMatchStrategy:
    name = MatchType.HISTORICAL.value

    @staticmethod
    def evaluate(request: "MatchRequest", candidate: MatchCandidate, history_signals: List[str]) -> float:
        if not history_signals:
            return 0.0
        base = 0.85
        boost = min(0.15, len(history_signals) * 0.05)
        return min(1.0, base + boost)

    @staticmethod
    def explain(request: "MatchRequest", candidate: MatchCandidate, history_signals: List[str]) -> MatchExplanation:
        return MatchExplanation(
            strategy_used=HistoricalMatchStrategy.name,
            match_signals=history_signals,
            confidence_factors={"historical_signal_count": len(history_signals)},
            fallback_strategies=[ExactMatchStrategy.name, NormalizedMatchStrategy.name],
            notes="Historical match evidence used to prefer a previously confirmed candidate.",
        )


from src.matching_runtime.strategies.exact_match_strategy import ExactMatchStrategy
from src.matching_runtime.strategies.normalized_match_strategy import NormalizedMatchStrategy
