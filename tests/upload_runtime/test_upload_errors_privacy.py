import json

import pytest

from src.upload_runtime import UploadCommand, UploadError, UploadErrorCode


@pytest.mark.parametrize("code", list(UploadErrorCode))
def test_upload_errors_use_fixed_non_reflective_messages(code):
    error = UploadError(code, field="upload")
    serialized = json.dumps(error.to_dict()).lower()
    assert error.code == code.value
    for forbidden in ("private", "token", "credential", "c:\\", "/home/", "traceback"):
        assert forbidden not in serialized


def test_command_metadata_error_does_not_reflect_private_value():
    with pytest.raises(ValueError) as rejected:
        UploadCommand(
            "upload-001", "tenant-001", "actor-001", "invoice.pdf", 1, "pdf", "api",
            metadata={"token": "private-secret-value"},
        )
    assert "private-secret-value" not in str(rejected.value)

