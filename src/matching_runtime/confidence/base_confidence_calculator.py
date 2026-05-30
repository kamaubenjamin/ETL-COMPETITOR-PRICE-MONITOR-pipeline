from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict

from src.matching_runtime.models.match_candidate import MatchCandidate
from src.matching_runtime.contracts.match_request import MatchRequest


class BaseConfidenceCalculator(ABC):
    @abstractmethod
    def calculate_confidence(self, candidate: MatchCandidate, request: MatchRequest) -> Dict[str, float]:
        ...

    @abstractmethod
    def determine_overall(self, factors: Dict[str, float]) -> float:
        ...
