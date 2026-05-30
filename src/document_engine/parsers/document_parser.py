"""Orchestrates the three existing parsers into a single ParsingResult.

No parsing logic lives here — this is a thin composition layer that invokes
the existing BlockParser, DocumentSectionDetector, and TableParser, and
adapts their outputs into canonical structural models.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.document_engine.parsers.block_parser import BlockParser
from src.document_engine.parsers.section_detector import DocumentSectionDetector
from src.document_engine.parsers.table_parser import TableParser
from src.document_engine.structure.models.canonical_table import CanonicalTable
from src.document_engine.structure.models.parsing_result import ParsingResult
from src.document_engine.structure.models.structural_block import StructuralBlock


class DocumentParser:
    """Composes the three existing parser passes for a single document.

    Usage::

        parser = DocumentParser()
        result = parser.parse(content)
    """

    def __init__(self) -> None:
        self._block_parser = BlockParser()
        self._section_detector = DocumentSectionDetector()
        self._table_parser = TableParser()

    def parse(self, content: str) -> ParsingResult:
        """Run all three parsers and return an aggregated ParsingResult.

        No side effects — no telemetry, no file I/O.
        """
        # 1. Block segmentation
        block_segment = self._block_parser.parse(content)
        blocks: List[StructuralBlock] = [
            StructuralBlock.from_text_block(tb) for tb in block_segment.blocks
        ]

        # 2. Section detection — keep as serializable dicts
        detected_sections = self._section_detector.detect_sections(content)
        sections: List[Dict[str, Any]] = [s.to_dict() for s in detected_sections]

        # 3. Table extraction from text content
        raw_tables = self._table_parser.extract_text_table(content)
        tables: List[CanonicalTable] = [
            CanonicalTable.from_normalized_table(nt) for nt in raw_tables
        ]

        return ParsingResult(blocks=blocks, sections=sections, tables=tables)