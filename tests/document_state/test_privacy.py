import math

import pytest

from src.document_state.privacy import (
    is_unsafe_field_name,
    json_value,
    reject_unsafe_fields,
    utc_timestamp,
    validate_safe_metadata,
)


@pytest.mark.parametrize(
    "key",
    [
        "raw_document", "document_bytes", "raw_rows", "rows", "old_value",
        "new_value", "correction_value", "artifact_payload", "stack_trace", "storage_path",
    ],
)
def test_sensitive_field_names_are_rejected(key):
    assert is_unsafe_field_name(key)
    with pytest.raises(ValueError, match="not safe"):
        reject_unsafe_fields({key: "private"})


def test_metadata_is_allowlisted_scalar_bounded_and_immutable():
    metadata = validate_safe_metadata({"correlation_id": "corr-001", "issue_count": 2, "mode": "preview"})
    assert dict(metadata) == {"correlation_id": "corr-001", "issue_count": 2, "mode": "preview"}
    with pytest.raises(TypeError):
        metadata["issue_count"] = 3
    with pytest.raises(ValueError, match="not allowlisted"):
        validate_safe_metadata({"customer_name": "private"})
    with pytest.raises(ValueError, match="JSON scalar"):
        validate_safe_metadata({"issue_count": [1, 2]})
    with pytest.raises(ValueError, match="finite"):
        validate_safe_metadata({"issue_count": math.inf})
    with pytest.raises(ValueError, match="bounded"):
        validate_safe_metadata({"issue_count": 10**20})


def test_timestamp_requires_utc_and_json_conversion_rejects_objects():
    assert utc_timestamp("2026-07-13T09:00:00Z", "created_at").endswith("Z")
    with pytest.raises(ValueError, match="UTC"):
        utc_timestamp("2026-07-13T12:00:00+03:00", "created_at")
    with pytest.raises(ValueError, match="non-JSON"):
        json_value(object())
