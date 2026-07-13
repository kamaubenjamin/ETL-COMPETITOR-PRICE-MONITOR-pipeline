import json
from dataclasses import FrozenInstanceError

import pytest

from src.document_state.writers.errors import DocumentStateWriterError, WriterErrorCode
from src.document_state.writers.results import WriterResult, WriterResultStatus


def test_all_result_statuses_serialize_safely():
    results = (
        WriterResult("success", "create_document", ("doc-001",), 1),
        WriterResult("skipped_idempotent", "append_audit", ("audit-001",), 1),
        WriterResult("conflict", "update_snapshot", error_code="version_conflict", message="Version conflict."),
        WriterResult("invalid_input", "map_result", error_code="invalid_command", message="Command is invalid."),
        WriterResult("failed", "append_event", error_code="repository_unavailable", message="Repository is unavailable."),
    )
    assert [item.status for item in results] == [item.value for item in WriterResultStatus]
    for result in results:
        json.dumps(result.to_dict())
        with pytest.raises(FrozenInstanceError):
            result.status = "failed"


def test_result_state_and_error_combinations_are_validated():
    with pytest.raises(ValueError):
        WriterResult("success", "operation", error_code="internal_error")
    with pytest.raises(ValueError):
        WriterResult("failed", "operation")
    with pytest.raises(ValueError):
        WriterResult("success", "operation", ("one",), 2)


@pytest.mark.parametrize("code", list(WriterErrorCode))
def test_writer_errors_use_fixed_privacy_safe_messages(code):
    error = DocumentStateWriterError(code, field="command")
    serialized = error.to_dict()
    assert serialized["code"] == code.value
    assert serialized["field"] == "command"
    assert "private" not in str(error)
    json.dumps(serialized)
