"""Composes structural validation and quality scoring for a single document.

This is the public entry point for the validation layer. It runs all structural
rules and the heuristic quality scorer, returning both results.
"""

from __future__ import annotations

from typing import Dict

from src.document_engine.contracts.document import Document
from src.document_engine.structure.models.parsing_result import ParsingResult
from src.document_engine.structure.models.validation_result import ValidationResult
from src.document_engine.validation.structural_validator import run_structural_validation


def run_validation(
    document: Document,
    parsing_result: ParsingResult,
    classification: Dict[str, object],
) -> ValidationResult:
    """Run structural validation against a parsed document.

    Args:
        document: The document being validated.
        parsing_result: Aggregated parsing output.
        classification: Classification result (may include ``confidence`` key).

    Returns:
        A ``ValidationResult`` with all rule outcomes.
    """
    return run_structural_validation(document, parsing_result)
