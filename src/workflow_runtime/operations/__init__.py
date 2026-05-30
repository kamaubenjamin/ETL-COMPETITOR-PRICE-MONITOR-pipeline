"""Workflow operations — executable runtime units for each stage type.

Each operation implements ``BaseStage`` and is registered in ``STAGE_REGISTRY``.
Operations use only public APIs from ``document_engine``.
"""

from src.workflow_runtime.operations.base import BaseStage, STAGE_REGISTRY
from src.workflow_runtime.operations.ingest_stage import IngestStage
from src.workflow_runtime.operations.transform_stage import TransformStage
from src.workflow_runtime.operations.filter_stage import FilterStage
from src.workflow_runtime.operations.fuzzy_match_stage import FuzzyMatchStage
from src.workflow_runtime.operations.compare_stage import CompareStage
from src.workflow_runtime.operations.alert_stage import AlertStage
from src.workflow_runtime.operations.report_stage import ReportStage
from src.workflow_runtime.operations.entity_extract_stage import EntityExtractStage

__all__ = [
    "BaseStage",
    "STAGE_REGISTRY",
    "AlertStage",
    "CompareStage",
    "EntityExtractStage",
    "FilterStage",
    "FuzzyMatchStage",
    "IngestStage",
    "ReportStage",
    "TransformStage",
]