from src.entity_runtime.confidence import ConfidenceScorer
from src.entity_runtime.contracts import EntitySet, LineItem
from src.entity_runtime.normalization import TextNormalizer
from src.entity_runtime.orchestration import EntityRuntimeOrchestrator
from src.entity_runtime.validation import EntityValidator


def test_text_normalizer_trims_whitespace():
    input_text = "  Supplier:\tABC Supplies\n  Address: 123 Market St  "
    expected = "Supplier: ABC Supplies Address: 123 Market St"
    assert TextNormalizer.normalize_whitespace(input_text) == expected


def test_confidence_scorer_computes_average_confidence():
    entities = [
        LineItem(description="Widget A", confidence=0.7),
        LineItem(description="Widget B", confidence=0.9),
    ]

    assert ConfidenceScorer().score(entities) == 0.8


def test_entity_validator_reports_missing_entities():
    entity_set = EntitySet(source_document_id="doc-1", extraction_metadata={}, created_at="2026-05-30T00:00:00Z")
    result = EntityValidator().validate(entity_set)

    assert result["entity_validation_passed"] is False
    assert "no_entities_extracted" in result["entity_validation_issues"]


def test_orchestrator_delegates_to_extraction_engine():
    class DummyEngine:
        def __init__(self):
            self.called = False

        def extract(self, pipeline_result):
            self.called = True
            return pipeline_result

    engine = DummyEngine()
    orchestrator = EntityRuntimeOrchestrator(engine)
    payload = {"data": "ok"}

    assert orchestrator.run(payload) == payload
    assert engine.called is True
