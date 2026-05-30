"""Deterministic document ingestion orchestration.

The orchestration layer composes existing modules into a sequential pipeline.
No business logic lives here — only coordination and debug artifact emission.
"""

from src.document_engine.orchestration.ingestion_pipeline import (
    IngestionPipeline,
    IngestionPipelineResult,
)

__all__ = [
    "IngestionPipeline",
    "IngestionPipelineResult",
]