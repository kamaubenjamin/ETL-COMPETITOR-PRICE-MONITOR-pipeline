"""Deterministic structural validation rules for parsed documents.

All rules are pure functions — no side effects, no file I/O, no telemetry.
Each rule returns a list of ValidationRuleResult instances.

The name ``structural_validator`` avoids ambiguity with API-level or
schema-level validation systems elsewhere in the codebase.
"""

from __future__ import annotations

from typing import Dict, List

from src.document_engine.contracts.document import Document
from src.document_engine.structure.models.canonical_table import CanonicalTable
from src.document_engine.structure.models.parsing_result import ParsingResult
from src.document_engine.structure.models.structural_block import StructuralBlock
from src.document_engine.structure.models.validation_result import ValidationResult, ValidationRuleResult


# ── individual rule functions ──────────────────────────────────────────


def validate_block_structure(blocks: List[StructuralBlock]) -> List[ValidationRuleResult]:
    """Check that the document has at least some body blocks and a reasonable block count."""
    results: List[ValidationRuleResult] = []

    if not blocks:
        results.append(
            ValidationRuleResult(
                rule_name="block_count_minimum",
                passed=False,
                severity="error",
                message="Document contains zero text blocks — content may be empty.",
            )
        )
        return results

    results.append(
        ValidationRuleResult(
            rule_name="block_count_minimum",
            passed=True,
            severity="info",
            message=f"Document contains {len(blocks)} text blocks.",
        )
    )

    body_blocks = [b for b in blocks if b.block_type in ("text", "line_items", "totals", "section_header")]
    if not body_blocks:
        results.append(
            ValidationRuleResult(
                rule_name="body_blocks_present",
                passed=False,
                severity="warning",
                message="No body content blocks detected — document may be header/footer only.",
            )
        )
    else:
        results.append(
            ValidationRuleResult(
                rule_name="body_blocks_present",
                passed=True,
                severity="info",
                message=f"Document has {len(body_blocks)} body content blocks.",
            )
        )

    return results


def validate_section_coverage(sections: List[Dict]) -> List[ValidationRuleResult]:
    """Check that key structural sections (line_items, totals, dates) are detected."""
    results: List[ValidationRuleResult] = []

    if not sections:
        results.append(
            ValidationRuleResult(
                rule_name="section_coverage",
                passed=False,
                severity="warning",
                message="No document sections detected — structural parsing may be incomplete.",
            )
        )
        return results

    section_types = {s.get("section_type", "") for s in sections}
    coverage_keywords = {"line_items_section", "totals_section", "dates_section", "supplier_section"}
    matched = coverage_keywords & section_types

    if len(matched) >= 2:
        results.append(
            ValidationRuleResult(
                rule_name="section_coverage",
                passed=True,
                severity="info",
                message=f"Detected {len(matched)} key structural sections: {', '.join(sorted(matched))}.",
            )
        )
    else:
        results.append(
            ValidationRuleResult(
                rule_name="section_coverage",
                passed=False,
                severity="warning",
                message=f"Only {len(matched)} key sections found: {', '.join(sorted(matched)) or 'none'}.",
            )
        )

    return results


def validate_table_quality(tables: List[CanonicalTable]) -> List[ValidationRuleResult]:
    """Check extracted tables for minimum quality criteria."""
    results: List[ValidationRuleResult] = []

    if not tables:
        results.append(
            ValidationRuleResult(
                rule_name="tables_extracted",
                passed=True,
                severity="info",
                message="No tables found — expected for text-heavy documents.",
            )
        )
        return results

    low_conf_tables = [t for t in tables if t.confidence_score < 0.5]
    if low_conf_tables:
        results.append(
            ValidationRuleResult(
                rule_name="table_confidence",
                passed=False,
                severity="warning",
                message=f"{len(low_conf_tables)} table(s) have low confidence scores (< 0.5).",
            )
        )
    else:
        results.append(
            ValidationRuleResult(
                rule_name="table_confidence",
                passed=True,
                severity="info",
                message=f"All {len(tables)} table(s) have acceptable confidence.",
            )
        )

    return results


def validate_content_quality(document: Document) -> List[ValidationRuleResult]:
    """Check basic content quality: non-empty, min length, metadata presence."""
    results: List[ValidationRuleResult] = []

    content = document.content or ""
    if not content.strip():
        results.append(
            ValidationRuleResult(
                rule_name="content_non_empty",
                passed=False,
                severity="error",
                message="Document content is empty.",
            )
        )
    elif len(content) < 20:
        results.append(
            ValidationRuleResult(
                rule_name="content_min_length",
                passed=False,
                severity="warning",
                message=f"Document content is very short ({len(content)} chars).",
            )
        )
    else:
        results.append(
            ValidationRuleResult(
                rule_name="content_min_length",
                passed=True,
                severity="info",
                message=f"Document content is {len(content)} characters.",
            )
        )

    metadata = document.metadata or {}
    if not metadata:
        results.append(
            ValidationRuleResult(
                rule_name="metadata_present",
                passed=False,
                severity="warning",
                message="Document has no metadata.",
            )
        )
    else:
        results.append(
            ValidationRuleResult(
                rule_name="metadata_present",
                passed=True,
                severity="info",
                message=f"Document has {len(metadata)} metadata fields.",
            )
        )

    return results


# ── public orchestrator ────────────────────────────────────────────────


def run_structural_validation(document: Document, parsing_result: ParsingResult) -> ValidationResult:
    """Run all structural validation rules against a parsed document.

    Args:
        document: The raw (or normalized) document from the ingestion pipeline.
        parsing_result: The aggregated parsing output.

    Returns:
        A ValidationResult containing all rule outcomes.
    """
    all_rules: List[ValidationRuleResult] = []

    all_rules.extend(validate_block_structure(parsing_result.blocks))
    all_rules.extend(validate_section_coverage(parsing_result.sections))
    all_rules.extend(validate_table_quality(parsing_result.tables))
    all_rules.extend(validate_content_quality(document))

    return ValidationResult.from_rules(all_rules)