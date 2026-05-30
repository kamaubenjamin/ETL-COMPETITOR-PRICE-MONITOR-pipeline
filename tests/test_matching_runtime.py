import json

import pytest

from src.entity_runtime.contracts.customer import Customer
from src.entity_runtime.contracts.entity_set import EntitySet
from src.workflow_runtime.contracts.execution_context import ExecutionContext
from src.workflow_runtime.operations.matching_stage import MatchingStage
from src.matching_runtime.contracts.match_request import MatchRequest
from src.matching_runtime.contracts.match_type import MatchType
from src.matching_runtime.confidence.customer_confidence_calculator import CustomerConfidenceCalculator
from src.matching_runtime.confidence.product_confidence_calculator import ProductConfidenceCalculator
from src.matching_runtime.confidence.supplier_confidence_calculator import SupplierConfidenceCalculator
from src.matching_runtime.models.match_candidate import MatchCandidate
from src.matching_runtime.models.match_explanation import MatchExplanation
from src.matching_runtime.models.match_result import MatchResult
from src.matching_runtime.models.match_set import MatchSet
from src.matching_runtime.repositories.historical_match_store import InMemoryHistoricalMatchStore
from src.matching_runtime.repositories.master_data_repository import InMemoryMasterDataRepository
from src.matching_runtime.services.matching_service import MatchingService
from src.matching_runtime.strategies.exact_match_strategy import ExactMatchStrategy
from src.matching_runtime.strategies.fuzzy_match_strategy import FuzzyMatchStrategy
from src.matching_runtime.strategies.historical_match_strategy import HistoricalMatchStrategy
from src.matching_runtime.strategies.normalized_match_strategy import NormalizedMatchStrategy


class TestMatchingContracts:
    def test_match_request_to_dict(self):
        request = MatchRequest(
            request_id="req-1",
            entity_id="entity-1",
            entity_type="customer",
            entity_data={"name": "Acme"},
            master_data_type="customer",
        )
        data = request.to_dict()
        assert data["request_id"] == "req-1"
        assert data["entity_type"] == "customer"
        assert data["entity_data"]["name"] == "Acme"

    def test_match_candidate_to_dict(self):
        explanation = MatchExplanation(
            strategy_used=MatchType.EXACT.value,
            match_signals=["exact_name"],
            confidence_factors={"exact_name": 1.0},
            fallback_strategies=[],
            notes="Exact match.",
        )
        candidate = MatchCandidate(
            candidate_id="cand-1",
            candidate_name="Acme",
            candidate_fields={"name": "Acme"},
            source="master_customer",
            similarity_score=1.0,
            match_explanation=explanation,
            confidence=1.0,
        )
        result = candidate.to_dict()
        assert result["candidate_id"] == "cand-1"
        assert result["match_explanation"]["strategy_used"] == MatchType.EXACT.value

    def test_match_explanation_to_dict(self):
        explanation = MatchExplanation(
            strategy_used=MatchType.NORMALIZED.value,
            match_signals=["normalized_name"],
            confidence_factors={"normalized_name": 0.95},
            fallback_strategies=[MatchType.EXACT.value],
            notes="Normalized comparison.",
        )
        data = explanation.to_dict()
        assert data["strategy_used"] == MatchType.NORMALIZED.value
        assert data["confidence_factors"]["normalized_name"] == 0.95

    def test_match_result_to_dict(self):
        explanation = MatchExplanation(
            strategy_used=MatchType.FUZZY.value,
            match_signals=["fuzzy_name"],
            confidence_factors={"name_similarity": 0.82},
            fallback_strategies=[MatchType.EXACT.value, MatchType.NORMALIZED.value],
            notes="Fuzzy match.",
        )
        candidate = MatchCandidate(
            candidate_id="cand-2",
            candidate_name="Widget A",
            candidate_fields={"name": "Widget A"},
            source="master_line_item",
            similarity_score=0.82,
            match_explanation=explanation,
            confidence=0.82,
        )
        match_result = MatchResult(
            request_id="req-2",
            entity_id="entity-2",
            matched=True,
            match_type=MatchType.FUZZY,
            best_match=candidate,
            all_candidates=[candidate],
            overall_confidence=0.82,
            explanation=explanation,
            created_at="2026-05-30T00:00:00Z",
        )
        data = match_result.to_dict()
        assert data["match_type"] == MatchType.FUZZY.value
        assert data["best_match"]["candidate_name"] == "Widget A"

    def test_match_set_to_dict(self):
        explanation = MatchExplanation(
            strategy_used=MatchType.MANUAL.value,
            match_signals=[],
            confidence_factors={},
            fallback_strategies=[],
            notes="No automated match.",
        )
        result = MatchResult(
            request_id="req-3",
            entity_id="entity-3",
            matched=False,
            match_type=MatchType.MANUAL,
            best_match=None,
            all_candidates=[],
            overall_confidence=0.0,
            explanation=explanation,
            created_at="2026-05-30T00:00:00Z",
        )
        match_set = MatchSet(
            source_document_id="doc-1",
            matches=[result],
            match_statistics={"total": 1, "matched": 0, "unmatched": 1},
            overall_confidence=0.0,
            matching_metadata={"threshold": 0.7},
            created_at="2026-05-30T00:00:00Z",
        )
        data = match_set.to_dict()
        assert data["source_document_id"] == "doc-1"
        assert data["matches"][0]["match_type"] == MatchType.MANUAL.value


class TestMatchingStrategies:
    def test_exact_match_strategy(self):
        request = MatchRequest(
            request_id="req-4",
            entity_id="entity-4",
            entity_type="customer",
            entity_data={"name": "Acme Corporation"},
            master_data_type="customer",
        )
        candidate = MatchCandidate(
            candidate_id="cust-001",
            candidate_name="Acme Corporation",
            candidate_fields={"name": "Acme Corporation"},
            source="master_customer",
            similarity_score=0.0,
            match_explanation=MatchExplanation(
                strategy_used="none",
                match_signals=[],
                confidence_factors={},
                fallback_strategies=[],
            ),
        )
        assert ExactMatchStrategy.evaluate(request, candidate) == 1.0
        explanation = ExactMatchStrategy.explain(request, candidate)
        assert explanation.strategy_used == MatchType.EXACT.value

    def test_normalized_match_strategy(self):
        request = MatchRequest(
            request_id="req-5",
            entity_id="entity-5",
            entity_type="customer",
            entity_data={"name": "  Acme  Corporation "},
            master_data_type="customer",
        )
        candidate = MatchCandidate(
            candidate_id="cust-001",
            candidate_name="acme corporation",
            candidate_fields={"name": "acme corporation"},
            source="master_customer",
            similarity_score=0.0,
            match_explanation=MatchExplanation(
                strategy_used="none",
                match_signals=[],
                confidence_factors={},
                fallback_strategies=[],
            ),
        )
        assert NormalizedMatchStrategy.evaluate(request, candidate) == 0.95
        assert NormalizedMatchStrategy.explain(request, candidate).strategy_used == MatchType.NORMALIZED.value

    def test_fuzzy_match_strategy(self):
        request = MatchRequest(
            request_id="req-6",
            entity_id="entity-6",
            entity_type="line_item",
            entity_data={"name": "Widget A S"},
            master_data_type="line_item",
        )
        candidate = MatchCandidate(
            candidate_id="prod-001",
            candidate_name="Widget A",
            candidate_fields={"name": "Widget A"},
            source="master_line_item",
            similarity_score=0.0,
            match_explanation=MatchExplanation(
                strategy_used="none",
                match_signals=[],
                confidence_factors={},
                fallback_strategies=[],
            ),
        )
        score = FuzzyMatchStrategy.evaluate(request, candidate)
        assert score > 0.75
        explanation = FuzzyMatchStrategy.explain(request, candidate)
        assert explanation.strategy_used == MatchType.FUZZY.value

    def test_historical_match_strategy(self):
        request = MatchRequest(
            request_id="req-7",
            entity_id="entity-7",
            entity_type="customer",
            entity_data={"name": "Acme Corporation"},
            master_data_type="customer",
        )
        candidate = MatchCandidate(
            candidate_id="cust-001",
            candidate_name="Acme Corporation",
            candidate_fields={"name": "Acme Corporation"},
            source="master_customer",
            similarity_score=0.0,
            match_explanation=MatchExplanation(
                strategy_used="none",
                match_signals=[],
                confidence_factors={},
                fallback_strategies=[],
            ),
        )
        score = HistoricalMatchStrategy.evaluate(request, candidate, ["cust-001"])
        assert score > 0.0
        assert HistoricalMatchStrategy.explain(request, candidate, ["cust-001"]).strategy_used == MatchType.HISTORICAL.value


class TestConfidenceCalculators:
    def test_customer_confidence_calculator(self):
        calculator = CustomerConfidenceCalculator()
        request = MatchRequest(
            request_id="req-8",
            entity_id="entity-8",
            entity_type="customer",
            entity_data={"name": "Acme", "address": "123 Main St", "email": "billing@acme.com"},
            master_data_type="customer",
        )
        candidate = MatchCandidate(
            candidate_id="cust-001",
            candidate_name="Acme",
            candidate_fields={"address": "123 Main St", "email": "billing@acme.com"},
            source="master_customer",
            similarity_score=1.0,
            match_explanation=MatchExplanation(
                strategy_used=MatchType.EXACT.value,
                match_signals=["exact_name"],
                confidence_factors={"exact_name": 1.0},
                fallback_strategies=[],
            ),
        )
        factors = calculator.calculate_confidence(candidate, request)
        assert factors["name"] == 1.0
        assert calculator.determine_overall(factors) == pytest.approx(1.0)

    def test_supplier_confidence_calculator(self):
        calculator = SupplierConfidenceCalculator()
        request = MatchRequest(
            request_id="req-9",
            entity_id="entity-9",
            entity_type="supplier",
            entity_data={"name": "Global Supplies", "vendor_code": "GLOB123", "phone": "555-0100"},
            master_data_type="supplier",
        )
        candidate = MatchCandidate(
            candidate_id="sup-001",
            candidate_name="Global Supplies",
            candidate_fields={"vendor_code": "GLOB123", "phone": "555-0100"},
            source="master_supplier",
            similarity_score=1.0,
            match_explanation=MatchExplanation(
                strategy_used=MatchType.EXACT.value,
                match_signals=["exact_name"],
                confidence_factors={"exact_name": 1.0},
                fallback_strategies=[],
            ),
        )
        factors = calculator.calculate_confidence(candidate, request)
        assert factors["vendor_code"] == 1.0
        assert calculator.determine_overall(factors) == pytest.approx(1.0)

    def test_product_confidence_calculator(self):
        calculator = ProductConfidenceCalculator()
        request = MatchRequest(
            request_id="req-10",
            entity_id="entity-10",
            entity_type="line_item",
            entity_data={"name": "Widget A", "brand": "Acme", "category": "widgets", "size": "small"},
            master_data_type="line_item",
        )
        candidate = MatchCandidate(
            candidate_id="prod-001",
            candidate_name="Widget A",
            candidate_fields={"brand": "Acme", "category": "widgets", "size": "small"},
            source="master_line_item",
            similarity_score=1.0,
            match_explanation=MatchExplanation(
                strategy_used=MatchType.EXACT.value,
                match_signals=["exact_name"],
                confidence_factors={"exact_name": 1.0},
                fallback_strategies=[],
            ),
        )
        factors = calculator.calculate_confidence(candidate, request)
        assert factors["brand"] == 1.0
        assert calculator.determine_overall(factors) == pytest.approx(1.0)


class TestMatchingService:
    def test_matching_service_exact_match(self):
        service = MatchingService()
        request = MatchRequest(
            request_id="req-11",
            entity_id="entity-11",
            entity_type="customer",
            entity_data={"name": "Acme Corporation", "address": "123 Main St", "email": "billing@acme.com"},
            master_data_type="customer",
        )
        result = service.match_request(request)
        assert result.matched is True
        assert result.match_type == MatchType.EXACT
        assert result.best_match is not None

    def test_matching_service_fuzzy_match(self):
        service = MatchingService()
        request = MatchRequest(
            request_id="req-12",
            entity_id="entity-12",
            entity_type="line_item",
            entity_data={"name": "Widget A S"},
            master_data_type="line_item",
        )
        result = service.match_request(request)
        assert result.match_type in {MatchType.FUZZY, MatchType.NORMALIZED, MatchType.EXACT}
        assert result.overall_confidence > 0.0

    def test_matching_service_historical_reuse(self):
        history_store = InMemoryHistoricalMatchStore()
        service = MatchingService(historical_store=history_store)
        request1 = MatchRequest(
            request_id="req-13",
            entity_id="entity-13",
            entity_type="customer",
            entity_data={"name": "Acme Corporation", "address": "123 Main St", "email": "billing@acme.com"},
            master_data_type="customer",
        )
        result1 = service.match_request(request1)
        assert result1.matched is True
        request2 = MatchRequest(
            request_id="req-14",
            entity_id="entity-14",
            entity_type="customer",
            entity_data={"name": "Acme Corporation", "address": "123 Main St", "email": "billing@acme.com"},
            master_data_type="customer",
        )
        result2 = service.match_request(request2)
        assert result2.match_type in {MatchType.EXACT, MatchType.NORMALIZED, MatchType.HISTORICAL}


class TestMatchingStageIntegration:
    def test_matching_stage_with_entity_dict(self):
        stage = MatchingStage(config={"master_data_type": "customer", "confidence_threshold": 0.7})
        ctx = ExecutionContext(
            pipeline_run_id="run-1",
            workspace_id="ws",
            workflow_id="wf-1",
            started_at="2026-05-30T00:00:00Z",
        )
        input_artifact = {
            "customers": [
                {
                    "entity_id": "entity-15",
                    "entity_type": "customer",
                    "name": "Acme Corporation",
                    "address": "123 Main St",
                    "email": "billing@acme.com",
                }
            ]
        }
        result = stage.run(input_artifact, ctx)
        assert result.status == "success"
        match_set = result.output_artifact
        assert isinstance(match_set, MatchSet)
        assert match_set.matches[0].matched is True

    def test_matching_stage_with_entity_set(self):
        customer = Customer(
            entity_id="entity-16",
            name="Acme Corporation",
            address="123 Main St",
            email="billing@acme.com",
        )
        entity_set = EntitySet(source_document_id="doc-2", customers=[customer])
        stage = MatchingStage(config={"confidence_threshold": 0.7})
        ctx = ExecutionContext(
            pipeline_run_id="run-2",
            workspace_id="ws",
            workflow_id="wf-2",
            started_at="2026-05-30T00:00:00Z",
        )
        result = stage.run(entity_set, ctx)
        assert result.status == "success"
        match_set = result.output_artifact
        assert isinstance(match_set, MatchSet)
        assert len(match_set.matches) == 1
        assert match_set.matches[0].match_type == MatchType.EXACT
