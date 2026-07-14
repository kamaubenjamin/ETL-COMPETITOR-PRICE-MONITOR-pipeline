import json

import pytest

from src.upload_runtime import (
    UploadActivationResult,
    UploadArtifactReference,
    UploadDocumentStateWriteIntent,
    UploadIngestionActivationIntent,
    UploadProcessingStatus,
)


NOW = "2026-07-14T10:00:00Z"


def reference():
    return UploadArtifactReference("artifact-001", "test_placeholder", "pdf", 100, NOW)


def test_processing_status_catalog_contains_required_phase_three_outcomes():
    assert {item.value for item in UploadProcessingStatus} == {
        "ingestion_requested", "processing_started", "failed", "deferred_staging_required",
        "unsupported_activation", "document_state_recorded",
    }


def test_ingestion_and_document_state_intents_are_safe_json_contracts():
    ingestion = UploadIngestionActivationIntent(
        "upload-001", "document-001", "tenant-001", "actor-001", "api", "pdf", reference(), NOW
    )
    state = UploadDocumentStateWriteIntent(
        "upload-001", "document-001", "tenant-001", "actor-001", "event-001",
        "invoice.pdf", "invoice", NOW, "artifact-001",
    )
    serialized = json.dumps({"ingestion": ingestion.to_dict(), "state": state.to_dict()}).lower()
    assert state.lifecycle_status == "received"
    for forbidden in ("file_path", "storage_path", "raw_content", "credential", "token", "stack_trace"):
        assert forbidden not in serialized


def test_activation_result_enforces_ingestion_requires_recorded_state():
    with pytest.raises(ValueError):
        UploadActivationResult("upload-001", "document-001", "ingestion_requested", "ingestion_accepted")

