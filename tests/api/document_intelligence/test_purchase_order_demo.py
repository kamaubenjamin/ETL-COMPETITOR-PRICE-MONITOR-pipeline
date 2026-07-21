from fastapi.testclient import TestClient
from src.api.document_intelligence.providers.facade_provider import (
    facade_provider,
    synthetic_purchase_order,
    uat_read_only_facade_provider,
)
from starlette.requests import Request

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.config import APIAuthConfig, APIAuthMode
from src.api.document_intelligence.routers.documents import get_purchase_order
from src.security.providers import create_local_demo_provider
from src.workflow_runtime.query_facade import InMemoryWorkflowQueryFacade
from tests.api.document_intelligence.supabase_auth_helpers import TENANT_ID, application as uat_application, token as uat_token


def _client(tenant_id: str) -> TestClient:
    return TestClient(create_document_intelligence_app(
        auth_config=APIAuthConfig(APIAuthMode.LOCAL_DEMO),
        identity_provider=create_local_demo_provider(tenant_id),
    ))


OWNER_HEADERS = {"x-local-identity": "tenant-admin"}


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


def test_local_fixture_namespace_lists_filters_and_opens_purchase_order():
    client = _client("tenant-uat")
    listed = client.get("/api/v1/documents", headers=OWNER_HEADERS)
    filtered = client.get("/api/v1/documents?document_type=purchase_order", headers=OWNER_HEADERS)
    detail = client.get("/api/v1/documents/doc-002", headers=OWNER_HEADERS)
    purchase_order = client.get("/api/v1/documents/doc-002/purchase-order", headers=OWNER_HEADERS)

    assert listed.status_code == filtered.status_code == detail.status_code == purchase_order.status_code == 200
    assert [item["document_id"] for item in listed.json()["data"]] == ["doc-002"]
    assert [(item["document_id"], item["document_type"]) for item in filtered.json()["data"]] == [("doc-002", "purchase_order")]
    assert (detail.json()["data"]["document_id"], detail.json()["data"]["document_type"]) == ("doc-002", "purchase_order")
    assert purchase_order.json()["data"]["document_type"] == "purchase_order"
    for suffix in ("processing", "validation", "matching"):
        assert client.get(f"/api/v1/documents/doc-002/{suffix}", headers=OWNER_HEADERS).status_code == 200


def test_wrong_tenant_and_nonexistent_documents_remain_concealed():
    wrong_tenant = _client("tenant-demo")
    filtered = wrong_tenant.get("/api/v1/documents?document_type=purchase_order", headers=OWNER_HEADERS)
    assert filtered.status_code == 200
    assert filtered.json()["data"] == []
    for path in ("/api/v1/documents/doc-002", "/api/v1/documents/doc-002/purchase-order", "/api/v1/documents/not-present", "/api/v1/documents/not-present/purchase-order"):
        response = wrong_tenant.get(path, headers=OWNER_HEADERS)
        assert response.status_code == 404
        assert response.json()["error"]["code"] in {"resource_not_found", "document_not_found"}


def test_exact_hosted_uat_supabase_configuration_exposes_all_purchase_order_reads():
    application = uat_application()
    client = TestClient(application)
    headers = {"Authorization": f"Bearer {uat_token()}"}
    assert application.state.document_intelligence_provider is uat_read_only_facade_provider
    assert application.state.document_intelligence_environment["app_env"] == "uat"
    assert application.state.platform_runtime_summary == {"mode": "compatibility_default", "composed": False}

    listed = client.get("/api/v1/documents", headers=headers)
    filtered = client.get("/api/v1/documents?document_type=purchase_order", headers=headers)
    detail = client.get("/api/v1/documents/doc-002", headers=headers)
    purchase_order = client.get("/api/v1/documents/doc-002/purchase-order", headers=headers)
    optional_processing_status = client.get(
        "/api/v1/documents/doc-002/processing-status", headers=headers
    )
    lifecycle_history = client.get("/api/v1/documents/doc-002/processing", headers=headers)

    assert listed.status_code == filtered.status_code == detail.status_code == purchase_order.status_code == 200
    assert [(item["document_id"], item["document_type"]) for item in listed.json()["data"]] == [("doc-002", "purchase_order")]
    assert [(item["document_id"], item["document_type"]) for item in filtered.json()["data"]] == [("doc-002", "purchase_order")]
    assert (detail.json()["data"]["document_id"], detail.json()["data"]["document_type"]) == ("doc-002", "purchase_order")
    assert purchase_order.json()["data"]["document_type"] == "purchase_order"
    assert optional_processing_status.status_code == 404
    assert optional_processing_status.json()["error"]["code"] == "document_processing_status_not_found"
    assert lifecycle_history.status_code == 200
    assert len(lifecycle_history.json()["data"]) == 2
    for suffix in ("processing", "validation", "matching"):
        assert client.get(f"/api/v1/documents/doc-002/{suffix}", headers=headers).status_code == 200


def test_hosted_uat_tenant_slug_alias_is_authoritative_and_bounded():
    other_membership = [{
        "tenant_id": "33333333-3333-4333-8333-333333333333",
        "role": "owner",
        "status": "active",
        "app_tenants": {"name": "Other UAT", "slug": "other-uat", "status": "active"},
    }]
    application = uat_application(rows=other_membership)
    client = TestClient(application)
    headers = {"Authorization": f"Bearer {uat_token()}"}
    listed = client.get("/api/v1/documents?document_type=purchase_order", headers=headers)
    detail = client.get("/api/v1/documents/doc-002", headers=headers)
    purchase_order = client.get("/api/v1/documents/doc-002/purchase-order", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["data"] == []
    assert detail.status_code == purchase_order.status_code == 404


def test_tenant_slug_aliases_are_disabled_for_ordinary_composed_providers():
    provider = facade_provider.__class__(InMemoryWorkflowQueryFacade())
    assert provider.list_documents(tenant_id=TENANT_ID, tenant_slug="flowsync-uat") == []


def test_hosted_uat_uses_authoritative_slug_when_display_name_does_not_match_fixture_scope():
    hosted_membership_shape = [{
        "tenant_id": TENANT_ID,
        "role": "owner",
        "status": "active",
        "app_tenants": {
            "name": "FlowSync Document Intelligence UAT",
            "slug": "flowsync-uat",
            "status": "active",
        },
    }]
    client = TestClient(uat_application(rows=hosted_membership_shape))
    headers = {"Authorization": f"Bearer {uat_token()}"}

    session = client.get("/api/v1/session", headers=headers)
    listed = client.get("/api/v1/documents", headers=headers)
    filtered = client.get("/api/v1/documents?document_type=purchase_order", headers=headers)
    detail = client.get("/api/v1/documents/doc-002", headers=headers)
    purchase_order = client.get("/api/v1/documents/doc-002/purchase-order", headers=headers)

    assert session.status_code == 200
    assert session.json()["data"]["tenant_slug"] == "flowsync-uat"
    assert listed.status_code == filtered.status_code == detail.status_code == purchase_order.status_code == 200
    assert [(item["document_id"], item["document_type"]) for item in listed.json()["data"]] == [("doc-002", "purchase_order")]
    assert [(item["document_id"], item["document_type"]) for item in filtered.json()["data"]] == [("doc-002", "purchase_order")]
