from __future__ import annotations

from typing import Dict

from src.matching_runtime.confidence.base_confidence_calculator import BaseConfidenceCalculator
from src.matching_runtime.contracts.match_request import MatchRequest
from src.matching_runtime.models.match_candidate import MatchCandidate
from src.matching_runtime.normalization.text_normalizer import TextNormalizer


class ProductConfidenceCalculator(BaseConfidenceCalculator):
    def calculate_confidence(self, candidate: MatchCandidate, request: MatchRequest) -> Dict[str, float]:
        name_value = 1.0 if TextNormalizer.compare_normalized(request.entity_data.get("name", ""), candidate.candidate_name) else 0.0
        brand_value = 1.0 if TextNormalizer.compare_normalized(request.entity_data.get("brand", ""), candidate.candidate_fields.get("brand", "")) else 0.0
        category_value = 1.0 if TextNormalizer.compare_normalized(request.entity_data.get("category", ""), candidate.candidate_fields.get("category", "")) else 0.0
        size_value = 1.0 if TextNormalizer.compare_normalized(request.entity_data.get("size", ""), candidate.candidate_fields.get("size", "")) else 0.0
        return {
            "name": name_value,
            "brand": brand_value,
            "category": category_value,
            "size": size_value,
        }

    def determine_overall(self, factors: Dict[str, float]) -> float:
        weights = {"name": 0.5, "brand": 0.2, "category": 0.2, "size": 0.1}
        return sum(factors.get(key, 0.0) * weight for key, weight in weights.items())
