from dataclasses import FrozenInstanceError
import json

import pytest

from src.upload_runtime import (
    UploadArtifactReference,
    UploadFileType,
    UploadProcessingIntent,
    UploadSource,
    UploadStatus,
    UploadValidationIssue,
    UploadValidationResult,
)


def test_foundational_catalogs_are_fixed_strings():
    assert {item.value for item in UploadFileType} == {"pdf", "csv", "xlsx", "txt", "eml"}
    assert {item.value for item in UploadStatus} == {
        "received", "validation_failed", "validated", "staged", "ingestion_requested",
        "processing_started", "completed", "failed", "duplicate_prevented",
    }
    assert UploadSource.FLOWSYNC.value == "flowsync"


def test_safe_contracts_are_immutable_and_json_serializable():
    reference = UploadArtifactReference("artifact-001", "test_placeholder", "pdf", 100, "2026-07-14T10:00:00Z")
    intent = UploadProcessingIntent("upload-001", "doc-001", requested_at="2026-07-14T10:00:00Z")
    issue = UploadValidationIssue("upload_empty", "file_size_bytes", "Upload is empty.")
    payload = {"reference": reference.to_dict(), "intent": intent.to_dict(), "validation": UploadValidationResult((issue,)).to_dict()}

    json.dumps(payload)
    assert "path" not in json.dumps(payload).lower()
    with pytest.raises(FrozenInstanceError):
        reference.reference_id = "changed"


def test_artifact_reference_rejects_zero_size_and_unknown_type():
    with pytest.raises(ValueError):
        UploadArtifactReference("artifact-001", "test", "xls", 100, "2026-07-14T10:00:00Z")
    with pytest.raises(ValueError):
        UploadArtifactReference("artifact-001", "test", "pdf", 0, "2026-07-14T10:00:00Z")

