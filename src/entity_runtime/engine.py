"""Entity Runtime v1 engine.

Deterministically extracts structured entities from a completed
Document Ingestion Pipeline result.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from src.document_engine.orchestration.ingestion_pipeline import IngestionPipelineResult
from src.document_engine.structure.models.canonical_table import CanonicalTable
from src.entity_runtime.confidence import ConfidenceScorer
from src.entity_runtime.contracts import (
    Customer,
    DocumentFinancials,
    DocumentReference,
    EntitySet,
    LineItem,
    SourceLineage,
    Supplier,
)
from src.entity_runtime.extraction import EntityExtractor
from src.entity_runtime.orchestration import EntityRuntimeOrchestrator
from src.entity_runtime.validation import EntityValidator


class EntityExtractionEngine:
    """Deterministic entity extraction engine for a single document."""

    def __init__(self, *, extraction_rule: str = "entity_runtime_v1"):
        self.extraction_rule = extraction_rule
        self._extractor = EntityExtractor(extraction_rule=extraction_rule)
        self._validator = EntityValidator()
        self._scorer = ConfidenceScorer()
        self.orchestrator = EntityRuntimeOrchestrator(self)

    def extract(self, pipeline_result: IngestionPipelineResult) -> EntitySet:
        if not hasattr(pipeline_result, "parsing_result"):
            raise ValueError("EntityExtractionEngine requires an IngestionPipelineResult artifact.")

        ingestion_result = pipeline_result.ingestion_result
        document = ingestion_result.normalized_document
        content = document.content or ""
        sections = pipeline_result.parsing_result.sections
        tables = pipeline_result.parsing_result.tables

        lineage = self._extractor._build_source_lineage(
            source_type=document.source.source_type,
            source_path=document.source.path,
            ingestion_id=ingestion_result.ingestion_id,
            pipeline_run_id=pipeline_result.pipeline_run_id,
        )

        references = self._extractor.extract_document_references(content, sections, pipeline_result.ingestion_result.classification, lineage)
        suppliers = self._extractor.extract_suppliers(content, sections, lineage)
        customers = self._extractor.extract_customers(content, sections, lineage)
        financials = self._extractor.extract_financials(content, sections, tables, lineage)
        line_items = self._extractor.extract_line_items(content, sections, tables, lineage)

        entities = [*references, *suppliers, *customers, *financials, *line_items]
        extraction_confidence = self._scorer.score(entities)

        base_metadata = {
            "document_type": ingestion_result.classification.get("document_type"),
            "section_types": [section.get("section_type") for section in sections],
            "table_count": len(tables),
            "validation_passed": getattr(pipeline_result.validation_result, "all_passed", False),
            "extraction_rule": self.extraction_rule,
        }

        temporary_entity_set = EntitySet(
            source_document_id=ingestion_result.ingestion_id,
            references=references,
            line_items=line_items,
            suppliers=suppliers,
            customers=customers,
            financials=financials,
            extraction_metadata=base_metadata,
            extraction_confidence=extraction_confidence,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        validation_metadata = self._validator.validate(temporary_entity_set)
        final_metadata = {**base_metadata, **validation_metadata}

        return EntitySet(
            source_document_id=temporary_entity_set.source_document_id,
            references=temporary_entity_set.references,
            line_items=temporary_entity_set.line_items,
            suppliers=temporary_entity_set.suppliers,
            customers=temporary_entity_set.customers,
            financials=temporary_entity_set.financials,
            extraction_metadata=final_metadata,
            extraction_confidence=temporary_entity_set.extraction_confidence,
            created_at=temporary_entity_set.created_at,
        )

    def _filter_entity_set(self, entity_set: EntitySet, entity_types: Set[str]) -> EntitySet:
        return EntitySet(
            source_document_id=entity_set.source_document_id,
            references=[e for e in entity_set.references if e.entity_type in entity_types],
            line_items=[e for e in entity_set.line_items if e.entity_type in entity_types],
            suppliers=[e for e in entity_set.suppliers if e.entity_type in entity_types],
            customers=[e for e in entity_set.customers if e.entity_type in entity_types],
            financials=[e for e in entity_set.financials if e.entity_type in entity_types],
            extraction_metadata=entity_set.extraction_metadata,
            extraction_confidence=entity_set.extraction_confidence,
            created_at=entity_set.created_at,
        )

