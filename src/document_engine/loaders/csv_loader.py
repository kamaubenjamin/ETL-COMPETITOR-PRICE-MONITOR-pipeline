from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

from src.document_engine.contracts.document import Document, DocumentSource


class CsvDocumentLoader:
    def load(self, file_path: str) -> Document:
        path = Path(file_path)
        rows: List[List[str]] = []
        fieldnames: List[str] = []
        row_count = 0

        with path.open("r", encoding="utf-8", errors="replace", newline="") as stream:
            sample = stream.read(4096)
            stream.seek(0)
            dialect = csv.Sniffer().sniff(sample) if sample else csv.excel
            reader = csv.reader(stream, dialect)
            for row in reader:
                if row_count == 0:
                    fieldnames = [cell.strip() for cell in row]
                rows.append([cell.strip() for cell in row])
                row_count += 1
                if row_count >= 200:
                    break

        content = "\n".join([",".join(row) for row in rows])
        metadata: Dict[str, object] = {
            "source_type": "csv",
            "field_count": len(fieldnames),
            "row_count": row_count,
            "fieldnames": fieldnames,
        }

        source = DocumentSource(
            path=str(path),
            source_type="csv",
            media_type="text/csv",
            encoding="utf-8",
        )

        return Document(source=source, content=content, metadata=metadata)
