from __future__ import annotations

import re
from typing import Dict, List

STOP_WORDS = {"the", "and", "of", "inc", "ltd", "co", "corp", "company", "limited", "llc"}


class TextNormalizer:
    @staticmethod
    def normalize_text(value: str) -> str:
        if not value:
            return ""
        normalized = value.strip().lower()
        normalized = re.sub(r"[\u2018\u2019\u201c\u201d]", "'", normalized)
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        normalized = normalized.strip()
        return normalized

    @staticmethod
    def normalize_entity_payload(entity_data: Dict[str, str]) -> Dict[str, str]:
        normalized: Dict[str, str] = {}
        for key, value in entity_data.items():
            if isinstance(value, str):
                normalized[key] = TextNormalizer.normalize_text(value)
            else:
                normalized[key] = value
        return normalized

    @staticmethod
    def extract_search_tokens(value: str) -> List[str]:
        normalized = TextNormalizer.normalize_text(value)
        tokens = [token for token in normalized.split() if token and token not in STOP_WORDS]
        return tokens

    @staticmethod
    def compare_normalized(a: str, b: str) -> bool:
        return TextNormalizer.normalize_text(a) == TextNormalizer.normalize_text(b)
