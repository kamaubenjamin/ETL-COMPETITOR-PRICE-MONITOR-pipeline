"""Lifecycle service composition from approved Document State ports."""

from __future__ import annotations

from src.document_state import DocumentStateComposition
from src.document_state.lifecycle import LifecycleAdvancementService


def compose_lifecycle_service(
    document_state: DocumentStateComposition,
) -> LifecycleAdvancementService:
    """Create the governed projection service without selecting a backend."""

    if not isinstance(document_state, DocumentStateComposition):
        raise ValueError("document_state must be a DocumentStateComposition")
    return LifecycleAdvancementService(document_state.reader, document_state.writer)
