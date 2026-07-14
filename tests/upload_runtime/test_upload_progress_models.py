from dataclasses import FrozenInstanceError
import json

import pytest

from src.upload_runtime import (
    UploadProcessingFailure,
    UploadProgressEvent,
    UploadProgressPage,
    UploadProgressStage,
    UploadProgressSummary,
    UploadProcessingTimeline,
)


NOW = "2026-07-14T10:00:00Z"


def test_progress_models_are_immutable_and_json_safe():
    summary = UploadProgressSummary(
        "upload-1", "processing_started", "processing_started", NOW, NOW,
        document_id="document-1", progress_percent=36, progress_approximate=True,
    )
    encoded = json.dumps(summary.to_dict())
    assert "processing_started" in encoded
    assert "tenant" not in encoded and "path" not in encoded
    with pytest.raises(FrozenInstanceError):
        summary.status = "completed"


def test_stage_and_timeline_ordering_are_deterministic():
    later = UploadProgressEvent(UploadProgressStage("validated", True, "2026-07-14T10:01:00Z"), "validated", "2026-07-14T10:01:00Z", "Validated.")
    earlier = UploadProgressEvent(UploadProgressStage("received", True, NOW), "received", NOW, "Received.")
    timeline = UploadProcessingTimeline("upload-1", (later, earlier))
    assert [event.stage.code for event in timeline.events] == ["received", "validated"]
    assert UploadProgressStage("staged", False).to_dict()["sequence"] == 2


def test_failed_summary_requires_safe_failure():
    failure = UploadProcessingFailure("internal_error", "Processing could not be completed.")
    summary = UploadProgressSummary("upload-1", "failed", "failed", NOW, NOW, failure=failure)
    assert summary.to_dict()["failure"]["code"] == "internal_error"
    with pytest.raises(ValueError):
        UploadProgressSummary("upload-1", "failed", "failed", NOW, NOW)


def test_progress_page_enforces_bounds():
    with pytest.raises(ValueError):
        UploadProgressPage((), 101, 0, 0)
    with pytest.raises(ValueError):
        UploadProgressPage((), 10, 10_001, 0)

