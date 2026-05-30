"""Canonical table model — adapter wrapping parser NormalizedTable output."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True, slots=True)
class CanonicalTable:
    """Immutable canonical table adapted from the parser's NormalizedTable.

    Uses composition: columns + rows are plain lists, no header/footer subclasses.
    """

    columns: List[str]
    rows: List[List[Optional[str]]]
    row_count: int
    column_count: int
    confidence_score: float = 0.0
    source_type: str = "unknown"
    quality_flags: List[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.quality_flags is None:
            object.__setattr__(self, "quality_flags", [])

    @classmethod
    def from_normalized_table(cls, normalized_table: Any) -> CanonicalTable:
        """Adapt a parser NormalizedTable into a canonical CanonicalTable.

        Accepts Any to avoid tight coupling; expects objects with the same
        shape as ``NormalizedTable`` (columns, rows, row_count, column_count,
        confidence_score, source_type, quality_flags).
        """
        quality_flags: List[str] = getattr(normalized_table, "quality_flags", None) or []
        return cls(
            columns=list(getattr(normalized_table, "columns", [])),
            rows=list(getattr(normalized_table, "rows", [])),
            row_count=getattr(normalized_table, "row_count", 0),
            column_count=getattr(normalized_table, "column_count", 0),
            confidence_score=getattr(normalized_table, "confidence_score", 0.0),
            source_type=getattr(normalized_table, "source_type", "unknown"),
            quality_flags=list(quality_flags),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["confidence_score"] = round(float(self.confidence_score), 2)
        return payload

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)