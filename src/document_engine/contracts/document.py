from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


DocumentMetadata = Dict[str, Any]


@dataclass(slots=True)
class DocumentSource:
    path: str
    source_type: str
    media_type: str
    encoding: Optional[str] = None

    def to_payload(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Document:
    source: DocumentSource
    content: str
    metadata: DocumentMetadata = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        serialized = {
            "source": self.source.to_payload(),
            "content": self.content,
            "metadata": {
                key: (value.isoformat() if isinstance(value, datetime) else value)
                for key, value in self.metadata.items()
            },
        }
        return serialized

    def to_json(self, **kwargs: Any) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)


@dataclass(slots=True)
class DocumentIngestionResult:
    document: Document
    classification: Dict[str, Any]
    normalized_document: Document
    ingestion_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document": self.document.to_dict(),
            "classification": self.classification,
            "normalized_document": self.normalized_document.to_dict(),
            "ingestion_id": self.ingestion_id,
        }
