import builtins
import os
import socket
from pathlib import Path

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.config import APIAuthConfig, APIAuthMode, APIEnvironmentConfig
from src.api.document_intelligence.providers.workflow_studio_provider import WorkflowStudioAPIProvider
from src.platform_runtime import RuntimeValidationError
from src.security.providers import create_local_demo_provider
from tests.api.document_intelligence.asgi_client import asgi_request


ROOT = Path(__file__).resolve().parents[3]


def _configure_uat_supabase(monkeypatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://project-ref.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test_fixture")


def test_api_startup_requires_no_network_or_filesystem_write(monkeypatch) -> None:
    _configure_uat_supabase(monkeypatch)
    real_open = builtins.open

    def guarded_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            raise AssertionError(f"startup attempted a filesystem write: {file}")
        return real_open(file, mode, *args, **kwargs)

    def unexpected_operation(*args, **kwargs):
        raise AssertionError("startup attempted external I/O")

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(socket, "create_connection", unexpected_operation)
    monkeypatch.setattr(socket.socket, "connect", unexpected_operation)
    monkeypatch.setattr(os, "mkdir", unexpected_operation)
    monkeypatch.setattr(os, "makedirs", unexpected_operation)

    application = create_document_intelligence_app(
        environment_config=APIEnvironmentConfig(app_env="uat")
    )

    assert application.state.platform_runtime is None
    assert isinstance(
        application.state.document_intelligence_workflow_studio_provider,
        WorkflowStudioAPIProvider,
    )


def test_uat_rejects_local_demo_header_authority() -> None:
    try:
        create_document_intelligence_app(
            auth_config=APIAuthConfig(APIAuthMode.LOCAL_DEMO),
            identity_provider=create_local_demo_provider("tenant-demo"),
            environment_config=APIEnvironmentConfig(app_env="uat"),
        )
    except RuntimeValidationError:
        pass
    else:
        raise AssertionError("UAT accepted local demo identity authority")


def test_default_uat_app_keeps_mutations_fail_closed_even_with_local_headers(monkeypatch) -> None:
    _configure_uat_supabase(monkeypatch)
    application = create_document_intelligence_app(
        environment_config=APIEnvironmentConfig(app_env="uat")
    )

    response = asgi_request(
        application,
        "POST",
        "/api/v1/workflow-definitions",
        headers={"x-local-identity": "admin", "x-tenant-id": "tenant-demo"},
        json_body={},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "authorization_denied"


def test_workflow_studio_provider_is_process_local_and_documented_as_ephemeral(monkeypatch) -> None:
    _configure_uat_supabase(monkeypatch)
    first = create_document_intelligence_app(environment_config=APIEnvironmentConfig(app_env="uat"))
    second = create_document_intelligence_app(environment_config=APIEnvironmentConfig(app_env="uat"))

    assert first.state.document_intelligence_workflow_studio_provider is not second.state.document_intelligence_workflow_studio_provider
    documentation = (
        ROOT / "docs" / "implementation" / "V0_21_PHASE_3_FASTAPI_VERCEL_COMPATIBILITY.md"
    ).read_text(encoding="utf-8").lower()
    for phrase in ("process-local", "ephemeral", "may disappear", "not durable"):
        assert phrase in documentation
