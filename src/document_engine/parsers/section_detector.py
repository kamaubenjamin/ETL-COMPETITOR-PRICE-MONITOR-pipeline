from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class DetectedSection:
    section_type: str
    start_line: int
    end_line: int
    content: str
    confidence: float = 0.5
    keywords_matched: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_type": self.section_type,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "line_count": self.end_line - self.start_line + 1,
            "confidence": round(float(self.confidence), 2),
            "keywords_matched": self.keywords_matched,
        }


class DocumentSectionDetector:
    SECTION_PATTERNS = {
        "supplier_section": {
            "keywords": ["supplier", "vendor", "from", "ship from", "sold by", "seller", "company", "bill from"],
            "min_confidence": 0.7,
        },
        "customer_section": {
            "keywords": ["customer", "to", "bill to", "ship to", "recipient", "buyer", "purchaser"],
            "min_confidence": 0.7,
        },
        "line_items_section": {
            "keywords": ["item", "qty", "quantity", "price", "amount", "description", "sku", "product", "line item"],
            "min_confidence": 0.8,
        },
        "totals_section": {
            "keywords": ["total", "subtotal", "grand total", "amount due", "balance", "net", "gross", "tax", "vat"],
            "min_confidence": 0.75,
        },
        "payment_section": {
            "keywords": ["payment", "pay to", "bank", "account", "swift", "iban", "check", "wire transfer", "payment terms"],
            "min_confidence": 0.7,
        },
        "delivery_section": {
            "keywords": ["delivery", "shipping", "freight", "logistics", "carrier", "tracking"],
            "min_confidence": 0.7,
        },
        "dates_section": {
            "keywords": ["date", "invoice date", "order date", "delivery date", "due date", "issued"],
            "min_confidence": 0.65,
        },
    }

    def __init__(self):
        self.section_regexes = {}
        for section_type, pattern in self.SECTION_PATTERNS.items():
            keywords = pattern["keywords"]
            regex_str = "|".join(f"\\b{re.escape(kw)}\\b" for kw in keywords)
            self.section_regexes[section_type] = re.compile(regex_str, re.IGNORECASE)

    def detect_sections(self, content: str) -> List[DetectedSection]:
        lines = content.split("\n")
        sections: List[DetectedSection] = []
        section_line_ranges: Dict[str, tuple[int, int]] = {}

        for line_idx, line in enumerate(lines):
            line_lower = line.lower()
            for section_type, regex in self.section_regexes.items():
                if regex.search(line_lower):
                    matched_keywords = regex.findall(line_lower)
                    if section_type not in section_line_ranges:
                        section_line_ranges[section_type] = (line_idx, line_idx)
                    else:
                        start_line, _ = section_line_ranges[section_type]
                        section_line_ranges[section_type] = (start_line, line_idx)

        for section_type, (start_line, end_line) in section_line_ranges.items():
            section_lines = lines[start_line : end_line + 1]
            section_content = "\n".join(section_lines)
            keywords_matched = self._extract_matched_keywords(section_content, section_type)
            confidence = min(0.95, 0.5 + len(keywords_matched) * 0.15)
            sections.append(
                DetectedSection(
                    section_type=section_type,
                    start_line=start_line,
                    end_line=end_line,
                    content=section_content,
                    confidence=confidence,
                    keywords_matched=keywords_matched,
                )
            )

        return sorted(sections, key=lambda s: s.start_line)

    def _extract_matched_keywords(self, content: str, section_type: str) -> List[str]:
        pattern = self.SECTION_PATTERNS[section_type]
        keywords = set()
        regex = self.section_regexes[section_type]
        for match in regex.finditer(content.lower()):
            keywords.add(match.group().lower())
        return sorted(list(keywords))

    def detect_line_items_structure(self, content: str) -> Dict[str, Any]:
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        line_item_count = 0
        numeric_lines = 0
        quantity_patterns = re.compile(r"\bqty\b|\bquantity\b|\bqt\b", re.IGNORECASE)
        price_patterns = re.compile(r"\$|€|£|¥|\d+\.\d{2}|\d+,\d{3}", re.IGNORECASE)

        for line in lines:
            if quantity_patterns.search(line) or price_patterns.search(line):
                line_item_count += 1
            if re.search(r"\d+", line):
                numeric_lines += 1

        return {
            "estimated_line_items": line_item_count,
            "numeric_lines": numeric_lines,
            "density_score": round(numeric_lines / (len(lines) or 1), 2),
        }
