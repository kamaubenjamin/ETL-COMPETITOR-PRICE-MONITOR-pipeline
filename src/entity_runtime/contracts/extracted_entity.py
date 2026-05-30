"""Abstract base for all extracted entity types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from src.entity_runtime.contracts.source_lineage import SourceLineage


class ExtractedEntity(ABC):
    """Abstract base for all extracted entities.

    Every entity has:
      - entity_id: UUID string, deterministic from content hash
      - entity_type: String discriminator matching the concrete type
      - confidence: 0.0–1.0 extraction confidence
      - source: Provenance lineage back to the original document
      - raw_text: Original text from the document

    Concrete subclasses add domain-specific fields.
    """

    @property
    @abstractmethod
    def entity_id(self) -> str:
        ...

    @property
    @abstractmethod
    def entity_type(self) -> str:
        ...

    @property
    @abstractmethod
    def confidence(self) -> float:
        ...

    @property
    @abstractmethod
    def source(self) -> SourceLineage:
        ...

    @property
    @abstractmethod
    def raw_text(self) -> str:
        ...

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        ...

    @abstractmethod
    def to_json(self, **kwargs: Any) -> str:
        ...