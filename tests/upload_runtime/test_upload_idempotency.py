from dataclasses import replace

import pytest

from src.upload_runtime import UploadCommand, upload_idempotency_key


FINGERPRINT_A = "a" * 64
FINGERPRINT_B = "b" * 64


def command(**overrides):
    values = dict(
        upload_id="upload-001", tenant_id="tenant-private", actor_id="actor-private",
        original_filename="private-invoice.pdf", file_size_bytes=1024, file_type="pdf", source="api",
        content_fingerprint=FINGERPRINT_A,
    )
    values.update(overrides)
    return UploadCommand(**values)


def test_idempotency_key_is_deterministic_opaque_and_json_safe():
    first = upload_idempotency_key(command())
    second = upload_idempotency_key(command())
    assert first == second
    assert first.value.startswith("upl_") and len(first.value) == 68
    assert "tenant-private" not in first.value
    assert "actor-private" not in first.value
    assert "private-invoice" not in first.value


@pytest.mark.parametrize(
    "changed",
    [
        {"content_fingerprint": FINGERPRINT_B}, {"file_size_bytes": 1025},
        {"original_filename": "private-invoice.csv", "file_type": "csv"},
    ],
)
def test_key_changes_with_fingerprint_size_or_type(changed):
    assert upload_idempotency_key(command(**changed)) != upload_idempotency_key(command())


def test_key_rejects_unvalidated_command():
    with pytest.raises(ValueError, match="pass upload validation"):
        upload_idempotency_key(command(tenant_id=None))

