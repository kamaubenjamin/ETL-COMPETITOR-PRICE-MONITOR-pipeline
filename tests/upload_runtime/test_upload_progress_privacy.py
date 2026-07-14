import json

import pytest

from src.upload_runtime import project_safe_upload_summary


def test_safe_projection_drops_unrecognized_raw_fields():
    summary = project_safe_upload_summary({
        "upload_id": "upload-1", "status": "received", "received_at": "2026-07-14T10:00:00Z",
        "file_path": "C:/secret/invoice.pdf", "raw_metadata": {"token": "secret"},
    })
    encoded = json.dumps(summary.to_dict())
    assert "secret" not in encoded and "file_path" not in encoded and "raw_metadata" not in encoded


def test_failure_projection_never_reflects_unknown_failure_text():
    summary = project_safe_upload_summary({
        "upload_id": "upload-1", "status": "failed", "received_at": "2026-07-14T10:00:00Z",
        "failure_code": "parser_crashed",
    })
    assert summary.failure.summary == "Processing could not be completed."


def test_unsafe_actor_or_source_labels_are_rejected():
    with pytest.raises(ValueError):
        project_safe_upload_summary({
            "upload_id": "upload-1", "status": "received", "received_at": "2026-07-14T10:00:00Z",
            "actor_label": "admin\nsecret",
        })

