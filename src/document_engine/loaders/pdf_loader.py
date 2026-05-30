from __future__ import annotations

from pathlib import Path
from typing import Dict

from src.document_engine.contracts.document import Document, DocumentSource

try:
    from pypdf import PdfReader
except ImportError as exc:
    PdfReader = None
    _PDF_IMPORT_ERROR = exc


class PdfDocumentLoader:
    def load(self, file_path: str) -> Document:
        if PdfReader is None:
            raise ImportError(
                "PDF ingestion requires the optional dependency 'pypdf'. "
                "Install it with `pip install pypdf` to enable PDF document support."
            ) from _PDF_IMPORT_ERROR

        path = Path(file_path)
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        content = "\n\n".join(pages).strip()

        metadata: Dict[str, object] = {
            "source_type": "pdf",
            "page_count": len(reader.pages),
            "title": getattr(reader.metadata, "/Title", None) if reader.metadata else None,
            "author": getattr(reader.metadata, "/Author", None) if reader.metadata else None,
        }

        source = DocumentSource(
            path=str(path),
            source_type="pdf",
            media_type="application/pdf",
        )
        return Document(source=source, content=content, metadata=metadata)
