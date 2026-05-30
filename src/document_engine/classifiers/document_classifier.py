from __future__ import annotations

from pathlib import Path
from typing import Dict

from src.document_engine.contracts.document import Document


def classify_document(document: Document) -> Dict[str, object]:
    source_type = document.source.source_type
    path = Path(document.source.path)
    extension = path.suffix.lower()
    content = document.content or ""
    confidence = 0.9 if source_type in {"pdf", "csv", "spreadsheet", "text", "email"} else 0.6
    document_type = source_type
    reason = f"extension:{extension}"

    if extension == ".eml" or source_type == "email":
        document_type = "email"
        confidence = 0.98
        reason = "email_header_present"
    elif extension in {".xlsx", ".xls"}:
        document_type = "spreadsheet"
        confidence = 0.96
        reason = "spreadsheet_extension"
    elif extension == ".csv":
        document_type = "csv"
        confidence = 0.95
        reason = "csv_extension"
    elif extension == ".txt":
        document_type = "text"
        confidence = 0.85
        reason = "text_extension"
    elif extension == ".pdf":
        document_type = "pdf"
        confidence = 0.95
        reason = "pdf_extension"
    elif "subject:" in content.lower() and "from:" in content.lower():
        document_type = "email"
        confidence = 0.75
        reason = "email_content_heuristic"
    elif "," in content and content.count("\n") > 2:
        document_type = "csv"
        confidence = 0.65
        reason = "csv_content_heuristic"

    return {
        "document_type": document_type,
        "source_type": source_type,
        "confidence": round(float(confidence), 2),
        "reason": reason,
    }
