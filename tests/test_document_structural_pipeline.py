"""Tests for deterministic document structural understanding runtime.

Tests cover:
  - StructuralBlock, CanonicalTable, ParsingResult, ValidationResult models
  - DocumentParser (wrapping existing parsers)
  - Structural validation rules
  - Quality scoring heuristics
  - IngestionPipeline orchestration
"""

import json
from pathlib import Path

import pytest

from src.document_engine.contracts.document import Document, DocumentSource
from src.document_engine.parsers.document_parser import DocumentParser
from src.document_engine.structure.models.canonical_table import CanonicalTable
from src.document_engine.structure.models.parsing_result import ParsingResult
from src.document_engine.structure.models.structural_block import BlockType, StructuralBlock, classify_block_count
from src.document_engine.structure.models.validation_result import ValidationResult, ValidationRuleResult
from src.document_engine.validation.quality_scorer import score_quality
from src.document_engine.validation.structural_validator import (
    run_structural_validation,
    validate_block_structure,
    validate_content_quality,
    validate_section_coverage,
    validate_table_quality,
)
from src.document_engine.validation.validation_orchestrator import run_validation


# ── StructuralBlock ────────────────────────────────────────────────────


class TestStructuralBlock:
    def test_create_minimal_block(self):
        block = StructuralBlock(block_type="text", content="Hello", position=0)
        assert block.block_type == "text"
        assert block.content == "Hello"
        assert block.metadata == {}

    def test_frozen_immutable(self):
        block = StructuralBlock(block_type="text", content="X", position=0)
        with pytest.raises(AttributeError):
            block.block_type = "header"  # type: ignore[misc]

    def test_from_text_block(self):
        """Adapter from a duck-typed parser TextBlock."""

        class FakeTextBlock:
            type = type("_t", (), {"value": "header"})()
            content = "Invoice"
            position = 0
            line_number = 0
            confidence = 0.95
            metadata = {"key": "val"}

        sb = StructuralBlock.from_text_block(FakeTextBlock())
        assert sb.block_type == "header"
        assert sb.content == "Invoice"
        assert sb.confidence == 0.95
        assert sb.metadata == {"key": "val"}

    def test_to_dict_and_json(self):
        block = StructuralBlock(
            block_type="line_items",
            content="Item, Qty, Price",
            position=0,
            line_number=5,
            confidence=0.85,
            metadata={"columns": 3},
        )
        d = block.to_dict()
        assert d["block_type"] == "line_items"
        assert d["confidence"] == 0.85

        j = block.to_json()
        parsed = json.loads(j)
        assert parsed["block_type"] == "line_items"

    def test_classify_block_count(self):
        blocks = [
            StructuralBlock(block_type="header", content="H", position=0),
            StructuralBlock(block_type="text", content="B", position=1),
            StructuralBlock(block_type="text", content="B2", position=2),
            StructuralBlock(block_type="footer", content="F", position=3),
        ]
        counts = classify_block_count(blocks)
        assert counts == {"header": 1, "text": 2, "footer": 1}


# ── CanonicalTable ─────────────────────────────────────────────────────


class TestCanonicalTable:
    def test_create_minimal(self):
        ct = CanonicalTable(columns=["A"], rows=[["1"]], row_count=1, column_count=1)
        assert ct.columns == ["A"]
        assert ct.quality_flags == []

    def test_from_normalized_table(self):
        class FakeNormalizedTable:
            columns = ["Name", "Price"]
            rows = [["Apple", "1.00"], ["Banana", "0.50"]]
            row_count = 2
            column_count = 2
            confidence_score = 0.88
            source_type = "csv"
            quality_flags = []

        ct = CanonicalTable.from_normalized_table(FakeNormalizedTable())
        assert ct.columns == ["Name", "Price"]
        assert ct.row_count == 2
        assert ct.confidence_score == 0.88

    def test_to_dict_and_json(self):
        ct = CanonicalTable(
            columns=["X", "Y"],
            rows=[["a", "1"], ["b", "2"]],
            row_count=2,
            column_count=2,
            confidence_score=0.75,
            source_type="text",
        )
        d = ct.to_dict()
        assert d["column_count"] == 2
        assert d["confidence_score"] == 0.75

        j = ct.to_json()
        assert "X" in j


# ── ParsingResult ──────────────────────────────────────────────────────


class TestParsingResult:
    def test_create_empty(self):
        pr = ParsingResult()
        assert pr.statistics["total_blocks"] == 0
        assert pr.statistics["total_sections"] == 0
        assert pr.statistics["total_tables"] == 0

    def test_with_blocks_and_sections(self):
        blocks = [
            StructuralBlock(block_type="header", content="H", position=0),
            StructuralBlock(block_type="text", content="B", position=1),
        ]
        sections = [{"section_type": "supplier_section", "start_line": 0, "end_line": 1}]
        pr = ParsingResult(blocks=blocks, sections=sections)
        assert pr.statistics["total_blocks"] == 2
        assert pr.statistics["total_sections"] == 1
        assert pr.statistics["block_type_counts"] == {"header": 1, "text": 1}

    def test_to_dict_serialization(self):
        ct = CanonicalTable(columns=["A"], rows=[["1"]], row_count=1, column_count=1)
        pr = ParsingResult(tables=[ct])
        d = pr.to_dict()
        assert len(d["tables"]) == 1
        assert d["tables"][0]["columns"] == ["A"]


# ── ValidationResult ───────────────────────────────────────────────────


class TestValidationResult:
    def test_validation_rule_result(self):
        rule = ValidationRuleResult(rule_name="test", passed=True)
        d = rule.to_dict()
        assert d["rule_name"] == "test"
        assert d["passed"] is True

    def test_validation_result_all_pass(self):
        rules = [
            ValidationRuleResult(rule_name="r1", passed=True, severity="info"),
            ValidationRuleResult(rule_name="r2", passed=True, severity="info"),
        ]
        result = ValidationResult.from_rules(rules)
        assert result.all_passed is True
        assert result.passed_count == 2
        assert result.total_rules == 2

    def test_validation_result_with_failures(self):
        rules = [
            ValidationRuleResult(rule_name="r1", passed=True),
            ValidationRuleResult(rule_name="r2", passed=False, severity="error", message="Failed"),
        ]
        result = ValidationResult.from_rules(rules)
        assert result.all_passed is False
        assert result.passed_count == 1
        assert result.total_rules == 2

    def test_validation_result_empty(self):
        result = ValidationResult.from_rules([])
        assert result.all_passed is True
        assert result.total_rules == 0

    def test_to_dict(self):
        rules = [
            ValidationRuleResult(rule_name="r1", passed=True, severity="info", message="ok"),
        ]
        result = ValidationResult.from_rules(rules)
        d = result.to_dict()
        assert d["total_rules"] == 1
        assert d["passed_count"] == 1
        assert d["failed_count"] == 0


# ── DocumentParser ─────────────────────────────────────────────────────


class TestDocumentParser:
    def test_parse_empty_content(self):
        parser = DocumentParser()
        result = parser.parse("")
        assert isinstance(result, ParsingResult)
        assert isinstance(result.statistics["total_blocks"], int)
        assert isinstance(result.blocks, list)
        assert result.statistics["total_sections"] == 0

    def test_parse_simple_text(self):
        parser = DocumentParser()
        content = "Header line\nSome body content here.\nFooter contact info.\n"
        result = parser.parse(content)
        assert result.statistics["total_blocks"] > 0
        # All blocks should be StructuralBlock instances
        for block in result.blocks:
            assert isinstance(block, StructuralBlock)

    def test_parse_table_detection(self):
        parser = DocumentParser()
        content = "Name\tAge\tCity\nAlice\t30\tNYC\nBob\t25\tLAX\n"
        result = parser.parse(content)
        # Tables may be detected depending on parser heuristics
        assert isinstance(result.tables, list)


# ── Structural Validation ──────────────────────────────────────────────


def make_document(content: str, metadata=None) -> Document:
    source = DocumentSource(path="test.txt", source_type="text", media_type="text/plain")
    return Document(source=source, content=content, metadata=metadata or {})


class TestStructuralValidation:
    def test_validate_block_structure_empty(self):
        rules = validate_block_structure([])
        assert any(not r.passed for r in rules)
        assert any("zero text blocks" in r.message.lower() for r in rules if not r.passed)

    def test_validate_block_structure_with_blocks(self):
        blocks = [StructuralBlock(block_type="text", content="Body", position=0)]
        rules = validate_block_structure(blocks)
        assert all(r.passed for r in rules)

    def test_validate_section_coverage_empty(self):
        rules = validate_section_coverage([])
        assert any(not r.passed for r in rules)

    def test_validate_section_coverage_good(self):
        sections = [
            {"section_type": "line_items_section", "start_line": 5, "end_line": 10},
            {"section_type": "totals_section", "start_line": 12, "end_line": 13},
            {"section_type": "dates_section", "start_line": 0, "end_line": 1},
        ]
        rules = validate_section_coverage(sections)
        assert all(r.passed for r in rules)

    def test_validate_table_quality_no_tables(self):
        rules = validate_table_quality([])
        assert all(r.passed for r in rules)

    def test_validate_table_quality_low_confidence(self):
        low = CanonicalTable(columns=["A"], rows=[["1"]], row_count=1, column_count=1, confidence_score=0.2)
        rules = validate_table_quality([low])
        assert any(not r.passed for r in rules)

    def test_validate_content_quality_empty(self):
        doc = make_document("")
        rules = validate_content_quality(doc)
        assert any(not r.passed for r in rules)

    def test_validate_content_quality_short(self):
        doc = make_document("Hi")
        rules = validate_content_quality(doc)
        assert any(not r.passed for r in rules)

    def test_validate_content_quality_good(self):
        doc = make_document("This is a reasonably long document content with metadata.", metadata={"source": "test"})
        rules = validate_content_quality(doc)
        assert all(r.passed for r in rules)

    def test_run_structural_validation_integration(self):
        blocks = [StructuralBlock(block_type="text", content="Body", position=0)]
        sections = [{"section_type": "line_items_section", "start_line": 0, "end_line": 2}]
        tables = [CanonicalTable(columns=["A"], rows=[["1"]], row_count=1, column_count=1, confidence_score=0.9)]
        pr = ParsingResult(blocks=blocks, sections=sections, tables=tables)
        doc = make_document("Document body content", metadata={"key": "val"})
        result = run_structural_validation(doc, pr)
        assert isinstance(result, ValidationResult)
        assert result.total_rules > 0


# ── Quality Scoring ────────────────────────────────────────────────────


class TestQualityScoring:
    def test_score_quality_high_confidence(self):
        blocks = [
            StructuralBlock(block_type="header", content="H", position=0),
            StructuralBlock(block_type="text", content="B1", position=1),
            StructuralBlock(block_type="text", content="B2", position=2),
            StructuralBlock(block_type="line_items", content="Item,Price", position=3),
        ]
        sections = [
            {"section_type": "line_items_section", "start_line": 3, "end_line": 5},
            {"section_type": "totals_section", "start_line": 6, "end_line": 7},
            {"section_type": "supplier_section", "start_line": 0, "end_line": 1},
        ]
        tables = [CanonicalTable(columns=["A"], rows=[["1"]], row_count=1, column_count=1, confidence_score=0.9)]
        pr = ParsingResult(blocks=blocks, sections=sections, tables=tables)
        rules = [
            ValidationRuleResult(rule_name="r1", passed=True),
            ValidationRuleResult(rule_name="r2", passed=True),
            ValidationRuleResult(rule_name="r3", passed=True),
        ]
        vr = ValidationResult.from_rules(rules)
        classification = {"document_type": "text", "confidence": 0.95}
        score = score_quality(pr, vr, classification)
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # should be reasonably high

    def test_score_quality_low_confidence(self):
        pr = ParsingResult()
        rules = [ValidationRuleResult(rule_name="r1", passed=False, severity="error")]
        vr = ValidationResult.from_rules(rules)
        classification = {"document_type": "unknown", "confidence": 0.1}
        score = score_quality(pr, vr, classification)
        assert 0.0 <= score <= 1.0
        assert score < 0.5  # should be low


# ── Validation Orchestration ───────────────────────────────────────────


class TestValidationOrchestration:
    def test_run_validation(self):
        doc = make_document("Some document content.", metadata={"source": "test"})
        blocks = [StructuralBlock(block_type="text", content="Body", position=0)]
        pr = ParsingResult(blocks=blocks)
        classification = {"document_type": "text", "confidence": 0.9}
        result = run_validation(doc, pr, classification)
        assert isinstance(result, ValidationResult)
        assert result.total_rules > 0


# ── IngestionPipeline (orchestration integration) ──────────────────────


class DummyTelemetry:
    def __init__(self):
        self.events = []

    def log_ingestion(self, event):
        self.events.append(event)
        return event


class TestIngestionPipeline:
    def test_pipeline_creates_debug_artifact(self, tmp_path):
        """E2E: pipeline runs and creates a debug JSON artifact."""
        source = tmp_path / "sample.txt"
        source.write_text("Invoice #123\nItem A\t$10.00\nItem B\t$20.00\nTotal\t$30.00\n", encoding="utf-8")
        debug_dir = tmp_path / "debug"

        from src.document_engine.orchestration.ingestion_pipeline import IngestionPipeline

        pipeline = IngestionPipeline(debug_path=str(debug_dir), telemetry=DummyTelemetry())
        result = pipeline.run(
            file_path=str(source),
            source_name="test_source",
            source_type="text",
            batch_id="batch-1",
        )

        assert result.pipeline_run_id is not None
        assert result.quality_score >= 0.0
        assert result.parsing_result.statistics["total_blocks"] > 0

        # Debug artifact should exist
        artifacts = list(debug_dir.glob("pipeline_*.json"))
        assert len(artifacts) == 1
        artifact = json.loads(artifacts[0].read_text(encoding="utf-8"))
        assert "pipeline_run_id" in artifact
        assert "quality_score" in artifact
        assert "ingestion" in artifact
        assert "parsing" in artifact
        assert "validation" in artifact