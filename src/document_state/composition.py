"""Explicit composition boundary for Document State repository backends."""

from __future__ import annotations

from dataclasses import dataclass

from .persistence import PersistenceBackend, PersistenceConfig, PersistenceError, require_active_backend
from .repositories import DocumentStateReadRepositories, DocumentStateWriteRepositories
from .repositories_in_memory import InMemoryDocumentStateRepositories


@dataclass(frozen=True, slots=True)
class DocumentStateComposition:
    """Selected backend and its deliberately separated repository surfaces."""

    backend: str
    reader: DocumentStateReadRepositories
    writer: DocumentStateWriteRepositories

    @property
    def is_durable(self) -> bool:
        return self.backend == PersistenceBackend.SQLITE.value


def compose_document_state(config: PersistenceConfig) -> DocumentStateComposition:
    """Construct exactly the requested repository backend with no fallback."""

    safe_config = require_active_backend(config)
    if safe_config.backend == PersistenceBackend.IN_MEMORY.value:
        repositories = InMemoryDocumentStateRepositories()
    elif safe_config.backend == PersistenceBackend.SQLITE.value:
        from .persistence.sqlite import SQLiteDocumentStateRepositories

        repositories = SQLiteDocumentStateRepositories(safe_config)
    else:
        raise PersistenceError("invalid_backend", field="backend")
    return DocumentStateComposition(
        backend=safe_config.backend,
        reader=repositories.reader,
        writer=repositories.writer,
    )
