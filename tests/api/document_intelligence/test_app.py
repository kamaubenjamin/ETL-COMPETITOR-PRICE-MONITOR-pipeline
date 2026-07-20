import inspect

from fastapi import FastAPI

from src.api.document_intelligence.app import create_document_intelligence_app


DOMAIN_PATHS = {
    "/api/v1/documents", "/api/v1/documents/{document_id}",
    "/api/v1/documents/{document_id}/processing",
    "/api/v1/documents/{document_id}/validation",
    "/api/v1/documents/{document_id}/matching", "/api/v1/review-cases",
    "/api/v1/review-cases/{review_case_id}",
    "/api/v1/review-cases/{review_case_id}/corrections",
    "/api/v1/reprocess-plans", "/api/v1/workflow-runs", "/api/v1/audit-events",
    "/api/v1/documents/{document_id}/exports", "/api/v1/export-attempts",
    "/api/v1/export-attempts/{attempt_id}",
    "/api/v1/documents/{document_id}/export/prepare",
    "/api/v1/documents/{document_id}/export",
    "/api/v1/documents/upload", "/api/v1/uploads", "/api/v1/uploads/{upload_id}",
    "/api/v1/uploads/{upload_id}/progress", "/api/v1/uploads/{upload_id}/timeline",
    "/api/v1/documents/{document_id}/processing-status",
    "/api/v1/workflow-definitions", "/api/v1/workflow-definitions/{workflow_id}",
    "/api/v1/workflow-definitions/{workflow_id}/versions",
    "/api/v1/workflow-definitions/{workflow_id}/versions/{version_id}",
    "/api/v1/workflow-definitions/{workflow_id}/audit", "/api/v1/workflow-operations",
    "/api/v1/workflow-definitions/{workflow_id}/versions/{version_id}/validate",
    "/api/v1/workflow-definitions/{workflow_id}/versions/{version_id}/test",
    "/api/v1/workflow-definitions/{workflow_id}/versions/{version_id}/submit",
    "/api/v1/workflow-definitions/{workflow_id}/versions/{version_id}/approve",
    "/api/v1/workflow-definitions/{workflow_id}/versions/{version_id}/publish",
    "/api/v1/workflow-definitions/{workflow_id}/deactivate",
    "/api/v1/workflow-definitions/{workflow_id}/archive",
}
EXPECTED_PATHS = {"/health", "/api/v1/health", "/api/v1/status", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"} | DOMAIN_PATHS


def test_app_factory_creates_separate_fastapi_application():
    application = create_document_intelligence_app()
    assert isinstance(application, FastAPI)
    assert application.title == "Document Intelligence API"
    assert application.version == "v1"


def test_only_expected_routes_are_registered():
    application = create_document_intelligence_app()
    concrete_routes = [route for route in application.routes if hasattr(route, "path")]
    built_in_paths = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
    api_paths = set(application.openapi()["paths"])
    assert {route.path for route in concrete_routes} == built_in_paths
    assert built_in_paths | api_paths == EXPECTED_PATHS


def test_openapi_contains_guarded_workflow_management_operations():
    schema = create_document_intelligence_app().openapi()
    assert set(schema["paths"]) == {"/health", "/api/v1/health", "/api/v1/status"} | DOMAIN_PATHS
    post_paths = {
        "/api/v1/documents/{document_id}/export/prepare",
        "/api/v1/documents/{document_id}/export",
        "/api/v1/documents/upload",
        "/api/v1/workflow-definitions/{workflow_id}/versions/{version_id}/validate",
        "/api/v1/workflow-definitions/{workflow_id}/versions/{version_id}/test",
        "/api/v1/workflow-definitions/{workflow_id}/versions/{version_id}/submit",
        "/api/v1/workflow-definitions/{workflow_id}/versions/{version_id}/approve",
        "/api/v1/workflow-definitions/{workflow_id}/versions/{version_id}/publish",
        "/api/v1/workflow-definitions/{workflow_id}/deactivate",
        "/api/v1/workflow-definitions/{workflow_id}/archive",
    }
    for path, operations in schema["paths"].items():
        expected = {"get", "post"} if path in {"/api/v1/workflow-definitions", "/api/v1/workflow-definitions/{workflow_id}/versions"} else {"get", "patch"} if path == "/api/v1/workflow-definitions/{workflow_id}/versions/{version_id}" else {"post"} if path in post_paths else {"get"}
        assert set(operations) == expected


def test_app_package_has_no_forbidden_runtime_or_competitor_imports():
    modules = [
        __import__("src.api.document_intelligence.app", fromlist=["*"]),
        __import__("src.api.document_intelligence.contracts", fromlist=["*"]),
        __import__("src.api.document_intelligence.responses", fromlist=["*"]),
        __import__("src.api.document_intelligence.routers.health", fromlist=["*"]),
    ]
    source = "\n".join(inspect.getsource(module) for module in modules).lower()
    for forbidden in (
        "document_engine", "entity_runtime", "matching_runtime", "review_runtime",
        "streamlit", "flowsync", "telemetry", "storage", "competitor",
    ):
        assert forbidden not in source
