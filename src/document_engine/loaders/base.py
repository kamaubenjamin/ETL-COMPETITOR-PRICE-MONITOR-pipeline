from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.document_engine.contracts.document import Document

SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".csv": "csv",
    ".xlsx": "xlsx",
    ".xls": "xlsx",
    ".txt": "text",
    ".eml": "email",
}


class DocumentLoader(ABC):
    @abstractmethod
    def load(self, file_path: str) -> "Document":
        raise NotImplementedError


def get_loader_for_path(file_path: str) -> DocumentLoader:
    extension = Path(file_path).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported document extension: {extension}")

    loader_map = {
        ".pdf": "src.document_engine.loaders.pdf_loader.PdfDocumentLoader",
        ".csv": "src.document_engine.loaders.csv_loader.CsvDocumentLoader",
        ".xlsx": "src.document_engine.loaders.xlsx_loader.XlsxDocumentLoader",
        ".xls": "src.document_engine.loaders.xlsx_loader.XlsxDocumentLoader",
        ".txt": "src.document_engine.loaders.txt_loader.TxtDocumentLoader",
        ".eml": "src.document_engine.loaders.email_loader.EmailDocumentLoader",
    }

    module_path = loader_map[extension]
    module_name, class_name = module_path.rsplit(".", 1)
    module = __import__(module_name, fromlist=[class_name])
    loader_class = getattr(module, class_name)
    return loader_class()
