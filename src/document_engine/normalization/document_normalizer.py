from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Optional

from src.document_engine.contracts.document import Document


WHITESPACE_PATTERN = re.compile(r"[\t\r\n]+")


def normalize_text(text: str) -> str:
    normalized = text.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    normalized = WHITESPACE_PATTERN.sub("\n", normalized).strip()
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized


def normalize_date(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d %b %Y", "%b %d, %Y"):
            try:
                parsed = datetime.fromisoformat(value)
                return parsed.isoformat()
            except ValueError:
                pass
        return value.strip()
    return str(value)


def normalize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for key, value in metadata.items():
        normalized_key = key.lower().replace(" ", "_")
        if normalized_key.endswith("date"):
            normalized[normalized_key] = normalize_date(value)
        else:
            normalized[normalized_key] = value
    return normalized


def normalize_document(document: Document) -> Document:
    content = normalize_text(document.content)
    metadata = normalize_metadata(document.metadata)
    return Document(source=document.source, content=content, metadata=metadata)
