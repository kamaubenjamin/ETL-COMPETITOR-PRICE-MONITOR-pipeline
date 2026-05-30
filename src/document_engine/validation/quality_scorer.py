"""Heuristic-only document quality scoring for telemetry signals.

This module produces a 0.0–1.0 quality score that is **not authoritative
business validation**. Scores are intended as telemetry signals to monitor
pipeline health and document quality trends over time.
"""

from __future__ import annotations

from typing import Dict, List

from src.document_engine.structure.models.canonical_table import CanonicalTable
from src.document_engine.structure.models.parsing_result import ParsingResult
from src.document_engine.structure.models.structural_block import StructuralBlock
from src.document_engine.structure.models.validation_result import ValidationResult


def score_quality(
    parsing_result: ParsingResult,
    validation_result: ValidationResult,
    classification: Dict[str, object],
) -> float:
    """Compute a heuristic quality score for telemetry purposes.

    Factors (weights):
      - Classification confidence  (25 %)
      - Block coverage             (25 %)
      - Section coverage           (25 %)
      - Validation pass rate       (25 %)

    Returns:
        A float in [0.0, 1.0] representing estimated structural quality.
    """
    # 1. Classification confidence factor
    class_conf: float = float(classification.get("confidence", 0.0) or 0.0)
    class_factor: float = class_conf  # 0.0–1.0

    # 2. Block coverage factor
    blocks: List[StructuralBlock] = parsing_result.blocks
    if not blocks:
        block_factor: float = 0.0
    else:
        body_count: int = sum(
            1 for b in blocks if b.block_type in ("text", "line_items", "totals", "section_header")
        )
        block_factor = min(1.0, body_count / max(len(blocks), 1) * 1.25)

    # 3. Section coverage factor
    sections: List[Dict] = parsing_result.sections
    if not sections:
        section_factor: float = 0.0
    else:
        # Reward documents that detected line_items, totals, supplier, or dates sections
        section_types: set = {s.get("section_type", "") for s in sections}
        key_sections: set = {"line_items_section", "totals_section", "supplier_section", "dates_section"}
        matched: int = len(key_sections & section_types)
        section_factor = min(1.0, matched / 3.0)  # 3+ key sections → 1.0

    # 4. Validation pass rate factor
    total: int = validation_result.total_rules
    passed: int = validation_result.passed_count
    validation_factor: float = passed / max(total, 1)

    # Weighted blend
    score: float = (
        class_factor * 0.25
        + block_factor * 0.25
        + section_factor * 0.25
        + validation_factor * 0.25
    )

    return round(float(score), 2)