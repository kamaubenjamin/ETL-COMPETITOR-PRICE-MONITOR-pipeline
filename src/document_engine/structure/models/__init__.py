"""Structural analysis models that wrap existing parser outputs."""

from src.document_engine.structure.models.structural_block import BlockType, StructuralBlock
from src.document_engine.structure.models.canonical_table import CanonicalTable
from src.document_engine.structure.models.parsing_result import ParsingResult
from src.document_engine.structure.models.validation_result import ValidationResult, ValidationRuleResult

__all__ = [
    "BlockType",
    "CanonicalTable",
    "ParsingResult",
    "StructuralBlock",
    "ValidationResult",
    "ValidationRuleResult",
]