"""Normalization utilities for Entity Runtime v1."""

from __future__ import annotations

import re


class TextNormalizer:
    """Canonical text normalization utilities for deterministic extraction."""

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    @staticmethod
    def normalize_label(label: str) -> str:
        return re.sub(r"[^\w\s]", " ", label or "").strip().lower()

    @staticmethod
    def normalize_currency(code: str) -> str:
        if not code:
            return ""
        return code.strip().upper()
