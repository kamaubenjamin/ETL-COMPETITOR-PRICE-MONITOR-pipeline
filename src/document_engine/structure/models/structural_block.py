"""Canonical structural block model — adapter wrapping parser TextBlock output."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


class BlockType:
    """Canonical block type constants. Mirrors the parser's BlockType enum
    values as plain strings to avoid a circular dependency between the
    parsers package and the models package.
    """

    HEADER = "header"
    FOOTER = "footer"
    METADATA = "metadata"
    SECTION_HEADER = "section_header"
    LINE_ITEMS = "line_items"
    TABLE = "table"
    TOTALS = "totals"
    TEXT = "text"
    WHITESPACE = "whitespace"


@dataclass(frozen=True, slots=True)
class StructuralBlock:
    """Immutable canonical block adapted from the parser's TextBlock.

    Uses composition over inheritance: block type is a discriminator field.
    """

    block_type: str
    content: str
    position: int
    line_number: Optional[int] = None
    confidence: float = 0.5
    metadata: Dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})

    @classmethod
    def from_text_block(cls, text_block: Any) -> StructuralBlock:
        """Adapt a parser TextBlock into a canonical StructuralBlock.

        Accepts Any to avoid tight coupling; expects objects with the same
        shape as ``TextBlock`` (type, content, position, line_number, confidence, metadata).
        """
        metadata = getattr(text_block, "metadata", {}) or {}
        return cls(
            block_type=text_block.type.value if hasattr(text_block.type, "value") else str(text_block.type),
            content=text_block.content,
            position=text_block.position,
            line_number=getattr(text_block, "line_number", None),
            confidence=getattr(text_block, "confidence", 0.5),
            metadata=dict(metadata),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["confidence"] = round(float(self.confidence), 2)
        return payload

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)


def classify_block_count(blocks: List[StructuralBlock]) -> Dict[str, int]:
    """Compute per-type block counts for telemetry statistics."""
    counts: Dict[str, int] = {}
    for block in blocks:
        counts[block.block_type] = counts.get(block.block_type, 0) + 1
    return counts