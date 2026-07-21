from src.api.document_intelligence.providers.facade_provider import facade_provider, synthetic_purchase_order
from starlette.requests import Request

from src.api.document_intelligence.routers.documents import get_purchase_order


def test_synthetic_purchase_order_schema_is_safe_and_exact():
    result = synthetic_purchase_order()
    assert result["document_type"] == "purchase_order"
    assert result["validation"]["is_valid"] is True
    assert result["subtotal"] == "400.00"
    assert result["tax"] == "64.00"
    assert result["total"] == "464.00"
    assert len(result["line_items"]) == 2
    serialized = str(result).casefold()
    assert ".local-uat-input" not in serialized
    assert "document-34" not in serialized
    assert "source_path" not in serialized


def test_facade_exposes_demo_only_for_visible_synthetic_purchase_order():
    assert facade_provider.get_purchase_order("doc-002") == synthetic_purchase_order()
    assert facade_provider.get_purchase_order("doc-001") is None
    assert facade_provider.get_purchase_order("missing") is None


def test_read_only_route_returns_canonical_safe_schema():
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    request.state.request_id = "request-purchase-order"
    response = get_purchase_order("doc-002", request)
    assert response["success"] is True
    assert set(response["data"]) == {
        "document_type", "purchase_order_number", "buyer", "supplier", "ship_to", "order_date",
        "delivery_date", "currency", "subtotal", "tax", "total", "line_items", "terms",
        "source_lineage", "validation", "extraction_warnings",
    }
