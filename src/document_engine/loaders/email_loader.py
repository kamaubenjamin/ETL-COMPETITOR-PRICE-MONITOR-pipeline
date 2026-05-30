from __future__ import annotations

from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Dict, Optional

from src.document_engine.contracts.document import Document, DocumentSource


class EmailDocumentLoader:
    def _extract_body(self, message) -> str:
        if message.is_multipart():
            parts = [self._extract_body(part) for part in message.iter_parts()]
            return "\n\n".join([part for part in parts if part])

        content_type = message.get_content_type()
        if content_type == "text/plain":
            return message.get_content().strip()
        return ""

    def load(self, file_path: str) -> Document:
        path = Path(file_path)
        raw_bytes = path.read_bytes()
        message = BytesParser(policy=policy.default).parsebytes(raw_bytes)

        body = self._extract_body(message)
        metadata: Dict[str, object] = {
            "source_type": "email",
            "subject": message.get("subject"),
            "from": message.get("from"),
            "to": message.get("to"),
            "date": message.get("date"),
            "content_type": message.get_content_type(),
        }

        content = "\n".join(
            [line.strip() for line in [message.get("subject", ""), body] if line]
        )
        source = DocumentSource(
            path=str(path),
            source_type="email",
            media_type="message/rfc822",
        )

        return Document(source=source, content=content, metadata=metadata)
