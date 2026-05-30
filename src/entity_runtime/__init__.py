"""Entity Runtime v1 — deterministic entity extraction, validation, and normalization.

Extracts structured entities (LineItem, Supplier, Customer, DocumentReference,
DocumentFinancials) from Document Runtime output. Produces immutable EntitySet.

Consumed by Workflow Runtime stages for transform, filter, match, and compare.
"""

from src.entity_runtime.contracts import (
    Customer,
    DocumentFinancials,
    DocumentReference,
    EntitySet,
    LineItem,
    SourceLineage,
    Supplier,
)
from src.entity_runtime.confidence import ConfidenceScorer
from src.entity_runtime.extraction import EntityExtractor
from src.entity_runtime.engine import EntityExtractionEngine
from src.entity_runtime.normalization import TextNormalizer
from src.entity_runtime.orchestration import EntityRuntimeOrchestrator
from src.entity_runtime.validation import EntityValidator

__all__ = [
    "Customer",
    "ConfidenceScorer",
    "DocumentFinancials",
    "DocumentReference",
    "EntityExtractionEngine",
    "EntityExtractor",
    "EntityRuntimeOrchestrator",
    "EntitySet",
    "LineItem",
    "SourceLineage",
    "Supplier",
    "TextNormalizer",
    "EntityValidator",
]
