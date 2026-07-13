import json

import pytest

from src.document_state.pagination import MAX_PAGE_LIMIT, PageRequest, PageResult
from src.document_state.records import DocumentRecord


TS = "2026-07-13T09:00:00+00:00"


def _record():
    return DocumentRecord(
        document_id="doc-001", filename="invoice.pdf", document_type="invoice",
        status="received", confidence=0.9, current_stage="ingest",
        received_at=TS, created_at=TS, updated_at=TS,
    )


@pytest.mark.parametrize(
    "kwargs",
    [{"limit": 0}, {"limit": MAX_PAGE_LIMIT + 1}, {"limit": True}, {"offset": -1}, {"offset": False}],
)
def test_page_request_rejects_invalid_bounds(kwargs):
    with pytest.raises(ValueError):
        PageRequest(**kwargs)


def test_page_result_is_immutable_bounded_and_json_compatible():
    result = PageResult(items=[_record()], total=1, limit=10, offset=0)
    assert isinstance(result.items, tuple)
    assert result.to_dict()["items"][0]["document_id"] == "doc-001"
    json.dumps(result.to_dict())


def test_page_result_rejects_invalid_counts_and_non_records():
    with pytest.raises(ValueError, match="pagination bounds"):
        PageResult(items=(_record(),), total=0, limit=10, offset=0)
    with pytest.raises(ValueError, match="serializable"):
        PageResult(items=(object(),), total=1, limit=10, offset=0)
