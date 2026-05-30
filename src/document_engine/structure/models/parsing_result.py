"""Aggregated parsing output combining all three parser outputs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from src.document_engine.structure.models.canonical_table import CanonicalTable
from src.document_engine.structure.models.structural_block import StructuralBlock, classify_block_count


@dataclass(frozen=True, slots=True)
class ParsingResult:
    """Immutable aggregate of all parser outputs for a single document.

    Contains adapted versions of the three parser results:
      - Structural blocks  (from BlockParser)
      - Detected sections  (from DocumentSectionDetector)
      - Canonical tables   (from TableParser)

    Statistics are computed at construction time — no lazy evaluation.
    """

    blocks: List[StructuralBlock] = field(default_factory=list)
    sections: List[Dict[str, Any]] = field(default_factory=list)
    tables: List[CanonicalTable] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.statistics:
            block_counts = classify_block_count(self.blocks)
            table_confidence = (
                round(float(sum(t.confidence_score for t in self.tables) / max(len(self.tables), 1)), 2)
                if self.tables
                else 0.0
            )
            section_types = [s.get("section_type", "unknown") for s in self.sections]
            object.__setattr__(
                self,
                "statistics",
                {
                    "total_blocks": len(self.blocks),
                    "total_sections": len(self.sections),
                    "total_tables": len(self.tables),
                    "block_type_counts": block_counts,
                    "section_types": section_types,
                    "average_table_confidence": table_confidence,
                },
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blocks": [b.to_dict() for b in self.blocks],
            "sections": self.sections,
            "tables": [t.to_dict() for t in self.tables],
            "statistics": self.statistics,
        }

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)