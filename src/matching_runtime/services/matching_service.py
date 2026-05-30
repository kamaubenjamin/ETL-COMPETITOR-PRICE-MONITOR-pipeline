from __future__ import annotations

import uuid
from dataclasses import replace
from typing import Any, Dict, List, Optional

from src.contracts.api import utc_now_iso
from src.matching_runtime.contracts.match_request import MatchRequest
from src.matching_runtime.contracts.match_type import MatchType
from src.matching_runtime.models.match_candidate import MatchCandidate
from src.matching_runtime.models.match_explanation import MatchExplanation
from src.matching_runtime.models.match_result import MatchResult
from src.matching_runtime.models.match_set import MatchSet
from src.matching_runtime.normalization.text_normalizer import TextNormalizer
from src.matching_runtime.confidence.customer_confidence_calculator import CustomerConfidenceCalculator
from src.matching_runtime.confidence.product_confidence_calculator import ProductConfidenceCalculator
from src.matching_runtime.confidence.supplier_confidence_calculator import SupplierConfidenceCalculator
from src.matching_runtime.repositories.master_data_repository import InMemoryMasterDataRepository
from src.matching_runtime.repositories.historical_match_store import InMemoryHistoricalMatchStore
from src.matching_runtime.strategies.exact_match_strategy import ExactMatchStrategy
from src.matching_runtime.strategies.normalized_match_strategy import NormalizedMatchStrategy
from src.matching_runtime.strategies.fuzzy_match_strategy import FuzzyMatchStrategy
from src.matching_runtime.strategies.historical_match_strategy import HistoricalMatchStrategy


class CandidateGenerator:
    def __init__(self, repository: InMemoryMasterDataRepository) -> None:
        self._repository = repository

    def generate_candidates(self, request: MatchRequest) -> List[MatchCandidate]:
        master_records = self._repository.list_candidates(request.master_data_type)
        candidates: List[MatchCandidate] = []

        for record in master_records:
            candidate_name = record.get("name", "")
            candidate = MatchCandidate(
                candidate_id=record.get("id", ""),
                candidate_name=candidate_name,
                candidate_fields=record,
                source=f"master_{request.master_data_type}",
                similarity_score=0.0,
                match_explanation=MatchExplanation(
                        strategy_used="none",
                        match_signals=[],
                        confidence_factors={},
                        fallback_strategies=[],
                        notes="No match evaluated yet.",
                ),
                confidence=0.0,
            )
            candidates.append(candidate)

        return candidates


class MatchingService:
    def __init__(
        self,
        master_data_repository: Optional[InMemoryMasterDataRepository] = None,
        historical_store: Optional[InMemoryHistoricalMatchStore] = None,
    ) -> None:
        self.master_data_repository = master_data_repository or InMemoryMasterDataRepository()
        self.historical_store = historical_store or InMemoryHistoricalMatchStore()
        self.candidate_generator = CandidateGenerator(self.master_data_repository)
        self.calculators = {
            "customer": CustomerConfidenceCalculator(),
            "supplier": SupplierConfidenceCalculator(),
            "line_item": ProductConfidenceCalculator(),
            "address": CustomerConfidenceCalculator(),
        }

    def match_request(self, request: MatchRequest) -> MatchResult:
        candidates = self.candidate_generator.generate_candidates(request)
        selected_candidates: List[MatchCandidate] = []
        explanation = MatchExplanation(
            strategy_used="none",
            match_signals=[],
            confidence_factors={},
            fallback_strategies=[],
            notes="No match produced.",
        )

        history_signals = self.historical_store.get_history_signals(request)

        for candidate in candidates:
            exact_score = ExactMatchStrategy.evaluate(request, candidate)
            if exact_score > 0:
                explanation = ExactMatchStrategy.explain(request, candidate)
                candidate = replace(candidate, similarity_score=1.0, confidence=1.0, match_explanation=explanation)
                selected_candidates = [candidate]
                break

        if not selected_candidates:
            for candidate in candidates:
                normalized_score = NormalizedMatchStrategy.evaluate(request, candidate)
                if normalized_score > 0:
                    explanation = NormalizedMatchStrategy.explain(request, candidate)
                    candidate = replace(candidate, similarity_score=0.95, confidence=normalized_score, match_explanation=explanation)
                    selected_candidates = [candidate]
                    break

        if not selected_candidates and history_signals:
            for candidate in candidates:
                historical_rate = HistoricalMatchStrategy.evaluate(request, candidate, history_signals)
                if historical_rate > 0:
                    explanation = HistoricalMatchStrategy.explain(request, candidate, history_signals)
                    candidate = replace(candidate, similarity_score=historical_rate, confidence=historical_rate, match_explanation=explanation)
                    selected_candidates = [candidate]
                    break

        if not selected_candidates:
            scored_candidates: List[MatchCandidate] = []
            calculator = self.calculators.get(request.entity_type)
            for candidate in candidates:
                score = FuzzyMatchStrategy.similarity_score(request.entity_data.get("name", ""), candidate.candidate_name)
                explanation = FuzzyMatchStrategy.explain(request, candidate)
                candidate = replace(candidate, similarity_score=score, match_explanation=explanation)
                if score >= FuzzyMatchStrategy.threshold:
                    factors = calculator.calculate_confidence(candidate, request) if calculator else {}
                    confidence = calculator.determine_overall(factors) if calculator else score
                    if confidence == 0.0:
                        confidence = score
                    candidate = replace(candidate, confidence=confidence)
                    scored_candidates.append(candidate)

            scored_candidates.sort(key=lambda item: item.confidence, reverse=True)
            selected_candidates = scored_candidates[:1] if not request.allow_multiple_matches else scored_candidates

        matched = bool(selected_candidates)
        best_match = selected_candidates[0] if selected_candidates else None
        overall_confidence = best_match.confidence if best_match else 0.0

        if best_match and best_match.confidence >= request.confidence_threshold:
            self.historical_store.add_match_evidence(request, best_match.candidate_id)

        match_type = MatchType.MANUAL
        if best_match:
            match_type = MatchType(next(
                (candidate.match_explanation.strategy_used for candidate in selected_candidates if candidate.match_explanation.strategy_used in {
                    MatchType.EXACT.value,
                    MatchType.NORMALIZED.value,
                    MatchType.FUZZY.value,
                    MatchType.HISTORICAL.value,
                }), MatchType.MANUAL.value
            ))

        match_result = MatchResult(
            request_id=request.request_id,
            entity_id=request.entity_id,
            matched=matched and overall_confidence >= request.confidence_threshold,
            match_type=match_type,
            best_match=best_match,
            all_candidates=selected_candidates,
            overall_confidence=overall_confidence,
            explanation=best_match.match_explanation if best_match else explanation,
            created_at=utc_now_iso(),
        )
        return match_result

    def match_batch(self, source_document_id: str, requests: List[MatchRequest], metadata: Optional[Dict[str, Any]] = None) -> MatchSet:
        results: List[MatchResult] = [self.match_request(request) for request in requests]
        overall_confidence = sum(result.overall_confidence for result in results) / max(len(results), 1)
        match_statistics = {
            "total": len(results),
            "matched": sum(1 for result in results if result.matched),
            "unmatched": sum(1 for result in results if not result.matched),
        }
        matching_metadata = {"confidence_thresholds": {request.request_id: request.confidence_threshold for request in requests}}
        return MatchSet(
            source_document_id=source_document_id,
            matches=results,
            match_statistics=match_statistics,
            overall_confidence=overall_confidence,
            matching_metadata=matching_metadata,
            created_at=utc_now_iso(),
        )
