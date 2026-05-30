from __future__ import annotations

from typing import Dict

from src.matching_runtime.confidence.base_confidence_calculator import BaseConfidenceCalculator
from src.matching_runtime.contracts.match_request import MatchRequest
from src.matching_runtime.models.match_candidate import MatchCandidate
from src.matching_runtime.normalization.text_normalizer import TextNormalizer


class SupplierConfidenceCalculator(BaseConfidenceCalculator):
    def calculate_confidence(self, candidate: MatchCandidate, request: MatchRequest) -> Dict[str, float]:
        name_value = 1.0 if TextNormalizer.compare_normalized(request.entity_data.get("name", ""), candidate.candidate_name) else 0.0
        vendor_code_value = 1.0 if request.entity_data.get("vendor_code") and request.entity_data.get("vendor_code") == candidate.candidate_fields.get("vendor_code") else 0.0
        contact_score = TextNormalizer.compare_normalized(request.entity_data.get("phone", ""), candidate.candidate_fields.get("phone", ""))
        contact_value = 1.0 if contact_score else 0.0
        return {
            "name": name_value,
            "vendor_code": vendor_code_value,
            "contact": contact_value,
        }

    def determine_overall(self, factors: Dict[str, float]) -> float:
        weights = {"name": 0.5, "vendor_code": 0.3, "contact": 0.2}
        return sum(factors.get(key, 0.0) * weight for key, weight in weights.items())
