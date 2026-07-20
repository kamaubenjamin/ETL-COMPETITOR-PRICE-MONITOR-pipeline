from starlette.requests import Request

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.config import APIAuthConfig, APIAuthMode
from src.security.providers import create_local_demo_provider


RULES = [{
    "rule_id": "rule-1", "name": "Filter", "stage": "validation", "order": 0,
    "actions": [{
        "action_id": "action-1", "action_type": "filter", "operation_name": "filter",
        "operation_version": "1", "source_path": "items",
    }],
}]


def app():
    return create_document_intelligence_app(
        auth_config=APIAuthConfig(APIAuthMode.LOCAL_DEMO),
        identity_provider=create_local_demo_provider("tenant-demo"),
    )


def request(application, identity="tenant-admin", tenant="tenant-demo", method="GET"):
    headers = []
    if identity:
        headers.append((b"x-local-identity", identity.encode("ascii")))
    if tenant:
        headers.append((b"x-tenant-id", tenant.encode("ascii")))
    value = Request({"type": "http", "method": method, "path": "/", "headers": headers, "app": application})
    value.state.request_id = "workflow-request-1"
    return value


def create_payload(workflow_id="workflow-1", version_id="version-1"):
    return {
        "workflow_id": workflow_id, "version_id": version_id, "name": "Invoice controls",
        "description": "Governed invoice workflow.", "business_domain": "banking",
        "document_type": "invoice", "change_summary": "Initial governed draft.", "rules": RULES,
    }
