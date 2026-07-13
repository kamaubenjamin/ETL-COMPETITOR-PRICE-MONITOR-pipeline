import json

import pytest

from src.api.document_intelligence.contracts import (
    PaginationMetadata,
    ResponseEnvelope,
    ResponseMetadata,
    SafeError,
)
from src.api.document_intelligence.responses import error_response, success_response


NOW = "2026-07-13T08:00:00+00:00"


def test_success_envelope_round_trip_is_json_compatible():
    payload = success_response(
        {"status": "ok"},
        request_id="request-001",
        metadata=ResponseMetadata(generated_at=NOW),
    )
    assert list(payload) == ["success", "data", "error", "metadata", "api_version", "request_id"]
    assert ResponseEnvelope.from_dict(payload).to_dict() == payload
    json.dumps(payload)


def test_safe_error_envelope_round_trip():
    payload = error_response(
        code="invalid_query",
        message="Query parameter is invalid.",
        request_id="request-002",
        details={"field": "limit"},
    )
    assert payload["success"] is False
    assert payload["data"] is None
    assert payload["error"] == {
        "code": "invalid_query",
        "message": "Query parameter is invalid.",
        "details": {"field": "limit"},
    }
    assert ResponseEnvelope.from_dict(payload).to_dict()["error"] == payload["error"]


def test_pagination_metadata_round_trip_and_bounds():
    pagination = PaginationMetadata(limit=50, offset=10, total=125)
    assert PaginationMetadata.from_dict(pagination.to_dict()) == pagination
    metadata = ResponseMetadata(generated_at=NOW, pagination=pagination)
    assert ResponseMetadata.from_dict(metadata.to_dict()) == metadata
    with pytest.raises(ValueError):
        PaginationMetadata(limit=201, offset=0, total=0)
    with pytest.raises(ValueError):
        PaginationMetadata(limit=50, offset=-1, total=0)


def test_contracts_reject_unknown_fields_and_invalid_invariants():
    with pytest.raises(ValueError):
        SafeError.from_dict({"code": "bad", "message": "Bad.", "details": {}, "raw": "private"})
    with pytest.raises(ValueError):
        ResponseEnvelope(
            success=True,
            data={},
            error=SafeError("bad", "Bad."),
            metadata=ResponseMetadata(generated_at=NOW),
            request_id="request-003",
        )
    with pytest.raises(ValueError):
        success_response(object(), request_id="request-004", metadata=ResponseMetadata(generated_at=NOW))
    with pytest.raises(ValueError):
        success_response(float("nan"), request_id="request-005", metadata=ResponseMetadata(generated_at=NOW))
    with pytest.raises(ValueError):
        ResponseMetadata(generated_at="2026-07-13T08:00:00")
    with pytest.raises(ValueError):
        ResponseEnvelope(
            success=True,
            data={},
            error=None,
            metadata=ResponseMetadata(generated_at=NOW),
            request_id="request-006",
            api_version="v2",
        )
