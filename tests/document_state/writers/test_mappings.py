import json

import pytest

from src.document_state.writers.errors import DocumentStateWriterError
from src.document_state.writers.mappings import WRITER_MAPPING_CATALOG, WriterMappingEvent, get_writer_mapping


EXPECTED = {
    "ingestion_received": ("document_record", "lifecycle_event"),
    "ingestion_classified": ("lifecycle_event", "processing_snapshot"),
    "parsing_structure_completed": ("processing_snapshot",),
    "validation_completed": ("validation_issue_records", "processing_snapshot"),
    "matching_completed": ("matching_summary_records", "processing_snapshot"),
    "review_required": ("review_reference", "lifecycle_event"),
    "correction_submitted": ("correction_summary", "audit_event"),
    "reprocess_planned": ("reprocess_plan", "lifecycle_event"),
    "workflow_run_completed": ("workflow_run", "audit_event"),
    "workflow_run_failed": ("workflow_run", "audit_event"),
}


def test_mapping_catalog_is_complete_deterministic_and_json_compatible():
    assert tuple(WRITER_MAPPING_CATALOG) == tuple(item.value for item in WriterMappingEvent)
    assert {key: value.record_targets for key, value in WRITER_MAPPING_CATALOG.items()} == EXPECTED
    assert json.dumps([item.to_dict() for item in WRITER_MAPPING_CATALOG.values()])


def test_required_lifecycle_and_processing_mappings_are_explicit():
    assert get_writer_mapping("ingestion_received").lifecycle_status == "received"
    assert get_writer_mapping("ingestion_classified").processing_stage == "classification"
    assert get_writer_mapping("validation_completed").processing_stage == "validate_data"
    assert get_writer_mapping("matching_completed").processing_stage == "matching"
    assert get_writer_mapping("reprocess_planned").lifecycle_status == "review_required"


def test_unknown_mapping_is_rejected_safely():
    with pytest.raises(DocumentStateWriterError) as raised:
        get_writer_mapping("unknown_stage")
    assert raised.value.code == "invalid_mapping"
    assert "unknown_stage" not in str(raised.value)
