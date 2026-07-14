"""Workflow Query Facade composition over Document State reads."""

from __future__ import annotations

from src.document_state import DocumentStateComposition
from src.document_state.adapters import DocumentStateQueryFacadeAdapter
from src.workflow_runtime.query_facade import WorkflowQueryFacadePort


def compose_query_facade(
    document_state: DocumentStateComposition,
    *,
    snapshot_at: str,
) -> WorkflowQueryFacadePort:
    """Create the read-only facade with an explicit deterministic snapshot clock."""

    if not isinstance(document_state, DocumentStateComposition):
        raise ValueError("document_state must be a DocumentStateComposition")
    return DocumentStateQueryFacadeAdapter(document_state.reader, snapshot_at=snapshot_at)
