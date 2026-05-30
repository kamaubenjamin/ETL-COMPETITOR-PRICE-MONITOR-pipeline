from __future__ import annotations

from typing import Dict

from src.matching_runtime.confidence.base_confidence_calculator import BaseConfidenceCalculator
from src.matching_runtime.contracts.match_request import MatchRequest
from src.matching_runtime.models.match_candidate import MatchCandidate
from src.matching_runtime.normalization.text_normalizer import TextNormalizer


class CustomerConfidenceCalculator(BaseConfidenceCalculator):
    def calculate_confidence(self, candidate: MatchCandidate, request: MatchRequest) -> Dict[str, float]:
        name_score = TextNormalizer.normalize_text(request.entity_data.get("name", "")) == TextNormalizer.normalize_text(candidate.candidate_name)
        name_value = 1.0 if name_score else 0.0
        address_score = TextNormalizer.compare_normalized(request.entity_data.get("address", ""), candidate.candidate_fields.get("address", ""))
        address_value = 1.0 if address_score else 0.0
        contact_score = TextNormalizer.compare_normalized(request.entity_data.get("email", ""), candidate.candidate_fields.get("email", ""))
        contact_value = 1.0 if contact_score else 0.0
        return {
            "name": name_value,
            "address": address_value,
            "contact": contact_value,
        }

    def determine_overall(self, factors: Dict[str, float]) -> float:
        weights = {"name": 0.6, "address": 0.25, "contact": 0.15}
        return sum(factors.get(key, 0.0) * weight for key, weight in weights.items())
