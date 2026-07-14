import json

import pytest

from src.upload_runtime import (
    UploadArtifactReference,
    UploadProcessingIntent,
    UploadResult,
    UploadValidationIssue,
)


NOW = "2026-07-14T10:00:00Z"


def test_safe_success_failure_staged_and_intent_results():
    issue = UploadValidationIssue("upload_empty", "file_size_bytes", "Upload is empty.")
    failed = UploadResult("validation_failed", "upload-001", "validation_failed", (issue,))
    staged = UploadResult("staged", "upload-001", artifact_reference=UploadArtifactReference("artifact-001", "test_placeholder", "pdf", 10, NOW))
    intended = UploadResult("ingestion_requested", "upload-001", processing_intent=UploadProcessingIntent("upload-001", "doc-001", requested_at=NOW))

    serialized = json.dumps([failed.to_dict(), staged.to_dict(), intended.to_dict()]).lower()
    assert failed.succeeded is False
    assert staged.succeeded and intended.succeeded
    for forbidden in ("file_path", "storage_path", "raw_content", "credential", "token", "stack_trace"):
        assert forbidden not in serialized


def test_result_consistency_rejects_invalid_combinations():
    with pytest.raises(ValueError):
        UploadResult("failed", "upload-001")
    with pytest.raises(ValueError):
        UploadResult("validated", "upload-001", error_code="internal_error")
    with pytest.raises(ValueError):
        UploadResult("validation_failed", "upload-001", error_code="validation_failed")
    with pytest.raises(ValueError):
        UploadResult("staged", "upload-001")
    with pytest.raises(ValueError):
        UploadResult("ingestion_requested", "upload-001")

