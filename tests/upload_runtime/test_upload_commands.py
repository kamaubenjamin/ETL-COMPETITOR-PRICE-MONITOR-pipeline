import json

import pytest

from src.upload_runtime import UploadCommand


def command(**overrides):
    values = dict(
        upload_id="upload-001", tenant_id="tenant-001", actor_id="actor-001",
        original_filename="invoice.pdf", file_size_bytes=1024, file_type="pdf", source="flowsync",
        declared_content_type="application/pdf", requested_at="2026-07-14T10:00:00Z",
        correlation_id="corr-001", request_id="req-001", metadata={"source_label": "inbox"},
    )
    values.update(overrides)
    return UploadCommand(**values)


def test_valid_upload_command_is_json_safe_and_has_no_content_or_path_fields():
    projected = command().to_dict()
    json.dumps(projected)
    assert projected["file_type"] == "pdf"
    assert projected["metadata"] == {"source_label": "inbox"}
    assert not any(key in projected for key in ("file_bytes", "file_content", "file_path", "storage_path"))


@pytest.mark.parametrize(
    "metadata",
    [
        {"safe": {"nested": "value"}}, {"file_bytes": "private"}, {"token": "private"},
        {"backend_path": "private"}, {"rows": [1, 2]}, {"payload": b"bytes"},
    ],
)
def test_command_rejects_nested_or_sensitive_metadata(metadata):
    with pytest.raises(ValueError):
        command(metadata=metadata)


def test_command_rejects_bytes_as_filename_and_invalid_source():
    with pytest.raises(ValueError):
        command(original_filename=b"raw bytes")
    with pytest.raises(ValueError):
        command(source="browser_secret_mode")


def test_missing_tenant_and_actor_are_representable_for_deterministic_validation():
    source = command(tenant_id=None, actor_id=None)
    assert source.tenant_id is None
    assert source.actor_id is None

