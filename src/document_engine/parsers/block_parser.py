from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class BlockType(str, Enum):
    HEADER = "header"
    FOOTER = "footer"
    METADATA = "metadata"
    SECTION_HEADER = "section_header"
    LINE_ITEMS = "line_items"
    TABLE = "table"
    TOTALS = "totals"
    TEXT = "text"
    WHITESPACE = "whitespace"


@dataclass(slots=True)
class TextBlock:
    type: BlockType
    content: str
    position: int
    line_number: Optional[int] = None
    confidence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "content": self.content,
            "position": self.position,
            "line_number": self.line_number,
            "confidence": round(float(self.confidence), 2),
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class DocumentBlockSegment:
    blocks: List[TextBlock] = field(default_factory=list)
    total_lines: int = 0
    total_blocks: int = 0
    header_lines: int = 0
    footer_lines: int = 0
    metadata_lines: int = 0
    body_lines: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blocks": [block.to_dict() for block in self.blocks],
            "statistics": {
                "total_lines": self.total_lines,
                "total_blocks": len(self.blocks),
                "header_lines": self.header_lines,
                "footer_lines": self.footer_lines,
                "metadata_lines": self.metadata_lines,
                "body_lines": self.body_lines,
            },
        }


class BlockParser:
    HEADER_KEYWORDS = {"invoice", "receipt", "order", "quote", "statement", "report", "bill"}
    FOOTER_KEYWORDS = {"thank", "contact", "phone", "email", "website", "signature", "terms"}
    TOTALS_KEYWORDS = {"total", "subtotal", "grand total", "amount due", "balance", "net", "gross"}
    LINE_ITEMS_KEYWORDS = {"item", "qty", "quantity", "price", "amount", "description", "sku"}
    SUPPLIER_KEYWORDS = {"supplier", "vendor", "from", "ship from", "sold by", "company", "seller"}
    PAYMENT_KEYWORDS = {"payment", "pay to", "bank", "account", "swift", "iban", "check"}
    DELIVERY_KEYWORDS = {"delivery", "ship to", "recipient", "address", "freight"}

    def __init__(self):
        self.header_pattern = re.compile("|".join(self.HEADER_KEYWORDS), re.IGNORECASE)
        self.footer_pattern = re.compile("|".join(self.FOOTER_KEYWORDS), re.IGNORECASE)
        self.totals_pattern = re.compile("|".join(self.TOTALS_KEYWORDS), re.IGNORECASE)
        self.line_items_pattern = re.compile("|".join(self.LINE_ITEMS_KEYWORDS), re.IGNORECASE)
        self.supplier_pattern = re.compile("|".join(self.SUPPLIER_KEYWORDS), re.IGNORECASE)
        self.payment_pattern = re.compile("|".join(self.PAYMENT_KEYWORDS), re.IGNORECASE)
        self.delivery_pattern = re.compile("|".join(self.DELIVERY_KEYWORDS), re.IGNORECASE)

    def parse(self, content: str) -> DocumentBlockSegment:
        lines = content.split("\n")
        blocks: List[TextBlock] = []
        position = 0
        header_lines = 0
        footer_lines = 0
        metadata_lines = 0
        body_lines = 0

        for line_num, line in enumerate(lines):
            stripped = line.strip()

            if not stripped:
                blocks.append(
                    TextBlock(
                        type=BlockType.WHITESPACE,
                        content=line,
                        position=position,
                        line_number=line_num,
                    )
                )
                position += len(line) + 1
                continue

            block_type, confidence = self._classify_line(stripped, line_num, len(lines))
            blocks.append(
                TextBlock(
                    type=block_type,
                    content=line,
                    position=position,
                    line_number=line_num,
                    confidence=confidence,
                )
            )

            if block_type == BlockType.HEADER:
                header_lines += 1
            elif block_type == BlockType.FOOTER:
                footer_lines += 1
            elif block_type == BlockType.METADATA:
                metadata_lines += 1
            elif block_type != BlockType.WHITESPACE:
                body_lines += 1

            position += len(line) + 1

        segment = DocumentBlockSegment(
            blocks=blocks,
            total_lines=len(lines),
            header_lines=header_lines,
            footer_lines=footer_lines,
            metadata_lines=metadata_lines,
            body_lines=body_lines,
        )
        return segment

    def _classify_line(self, line: str, line_num: int, total_lines: int) -> tuple[BlockType, float]:
        line_lower = line.lower()
        lines_from_end = total_lines - line_num

        if line_num < 5 and self.header_pattern.search(line_lower):
            return BlockType.HEADER, 0.95

        if lines_from_end < 5 and self.footer_pattern.search(line_lower):
            return BlockType.FOOTER, 0.92

        if self.totals_pattern.search(line_lower):
            return BlockType.TOTALS, 0.88

        if self.line_items_pattern.search(line_lower):
            return BlockType.LINE_ITEMS, 0.85

        if any(kw in line_lower for kw in ["date:", "ref:", "po", "invoice #", "order #", "id:"]):
            return BlockType.METADATA, 0.80

        if self.supplier_pattern.search(line_lower) or self.payment_pattern.search(line_lower):
            return BlockType.SECTION_HEADER, 0.75

        return BlockType.TEXT, 0.5
