"""Confidence scoring for Entity Runtime v1."""

from __future__ import annotations

from typing import Any, Iterable


class ConfidenceScorer:
    """Computes an aggregate confidence score across extracted entities."""

    def score(self, entities: Iterable[Any]) -> float:
        confidences = [float(getattr(entity, "confidence", 0.0)) for entity in entities if getattr(entity, "confidence", None) is not None]
        if not confidences:
            return 0.0
        return round(sum(confidences) / len(confidences), 2)
