from __future__ import annotations

from pathlib import Path
from typing import Dict

from src.document_engine.contracts.document import Document, DocumentSource


class TxtDocumentLoader:
    def load(self, file_path: str) -> Document:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8", errors="replace")
        metadata: Dict[str, object] = {
            "source_type": "text",
            "encoding": "utf-8",
            "line_count": content.count("\n") + 1,
        }

        source = DocumentSource(
            path=str(path),
            source_type="text",
            media_type="text/plain",
            encoding="utf-8",
        )
        return Document(source=source, content=content, metadata=metadata)
