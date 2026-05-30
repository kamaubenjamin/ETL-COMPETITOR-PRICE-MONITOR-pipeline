from __future__ import annotations

from enum import Enum


class MatchType(str, Enum):
    EXACT = "exact"
    NORMALIZED = "normalized"
    FUZZY = "fuzzy"
    HISTORICAL = "historical"
    MANUAL = "manual"
