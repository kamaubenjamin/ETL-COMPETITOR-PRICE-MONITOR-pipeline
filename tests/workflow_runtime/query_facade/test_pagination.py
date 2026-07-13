from dataclasses import FrozenInstanceError
import json

import pytest

from src.workflow_runtime.query_facade.pagination import MAX_PAGE_LIMIT, PageRequest, PageResult
from src.workflow_runtime.query_facade.read_models import DocumentInboxItem


def _document(document_id="doc-001"):
    return DocumentInboxItem(
        document_id=document_id,
        filename="invoice.pdf",
        document_type="invoice",
        status="validated",
        confidence=0.98,
        current_stage="validate_data",
        received_at="2026-07-01T08:00:00+00:00",
    )


def test_page_request_defaults_bounds_and_immutability():
    request = PageRequest()
    assert request.to_dict() == {"limit": 50, "offset": 0}
    assert PageRequest(limit=MAX_PAGE_LIMIT, offset=10).limit == 200
    with pytest.raises(FrozenInstanceError):
        request.limit = 10


@pytest.mark.parametrize(
    "kwargs",
    [
        {"limit": 0}, {"limit": 201}, {"limit": True}, {"limit": 1.5},
        {"offset": -1}, {"offset": True}, {"offset": 1.5},
    ],
)
def test_invalid_pagination_is_rejected(kwargs):
    with pytest.raises(ValueError):
        PageRequest(**kwargs)


def test_page_result_is_tuple_backed_and_json_compatible():
    page = PageResult(
        items=[_document()],
        total=1,
        limit=50,
        offset=0,
        snapshot_at="2026-07-01T08:01:00+00:00",
    )
    assert isinstance(page.items, tuple)
    assert page.to_dict()["items"][0]["document_id"] == "doc-001"
    json.dumps(page.to_dict())


def test_page_result_enforces_bounds_timestamp_and_serializable_items():
    with pytest.raises(ValueError, match="pagination bounds"):
        PageResult((_document(), _document("doc-002")), total=1, limit=1, offset=0, snapshot_at="2026-07-01T08:01:00+00:00")
    with pytest.raises(ValueError, match="timezone"):
        PageResult((), total=0, limit=1, offset=0, snapshot_at="2026-07-01T08:01:00")
    with pytest.raises(ValueError, match="serializable"):
        PageResult((object(),), total=1, limit=1, offset=0, snapshot_at="2026-07-01T08:01:00+00:00")
