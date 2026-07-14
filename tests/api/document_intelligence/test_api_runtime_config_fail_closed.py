import json

import pytest

from src.api.document_intelligence.app import create_document_intelligence_app
from src.platform_runtime import (
    ApiConfig,
    AuthConfig,
    BackendConfig,
    RuntimeConfig,
    RuntimeValidationError,
    StreamlitConfig,
)


NOW = "2026-07-14T13:00:00+00:00"


def _production(backend):
    return RuntimeConfig(
        "production",
        backend,
        AuthConfig("production", identity_provider="external", identity_provider_available=True, identity_provider_reference="secret://identity"),
        ApiConfig("read_only_guarded"),
        StreamlitConfig("api_preview"),
    )


@pytest.mark.parametrize(
    "config",
    [
        _production(BackendConfig("future_postgres")),
        _production(BackendConfig("in_memory")),
        _production(BackendConfig("sqlite", sqlite_path="private/production.sqlite3")),
        RuntimeConfig(
            "local",
            BackendConfig("sqlite"),
            AuthConfig("disabled"),
            ApiConfig("read_only_unguarded"),
            StreamlitConfig("local_preview"),
        ),
    ],
)
def test_invalid_runtime_config_never_falls_back_to_default_app(config):
    with pytest.raises(RuntimeValidationError) as raised:
        create_document_intelligence_app(runtime_config=config, snapshot_at=NOW)
    serialized = json.dumps(raised.value.to_dict())
    assert "private/production.sqlite3" not in serialized
    assert "secret://identity" not in serialized


def test_authenticated_placeholder_rejects_before_runtime_resource_construction(monkeypatch, tmp_path):
    called = False

    def unexpected(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("runtime construction must not start")

    monkeypatch.setattr("src.api.document_intelligence.app.compose_runtime", unexpected)
    config = RuntimeConfig(
        "pilot",
        BackendConfig("sqlite", sqlite_path=str(tmp_path / "pilot.sqlite3")),
        AuthConfig("authenticated", identity_provider="external", identity_provider_available=True),
        ApiConfig("read_only_guarded"),
        StreamlitConfig("api_preview"),
    )
    with pytest.raises(RuntimeValidationError) as raised:
        create_document_intelligence_app(runtime_config=config, snapshot_at=NOW)
    assert raised.value.code.value == "composition_failed"
    assert called is False


def test_runtime_and_legacy_auth_inputs_cannot_be_mixed():
    config = RuntimeConfig(
        "local",
        BackendConfig("in_memory"),
        AuthConfig("disabled"),
        ApiConfig("read_only_unguarded"),
        StreamlitConfig("local_preview"),
    )
    from src.api.document_intelligence.config import APIAuthConfig

    with pytest.raises(RuntimeValidationError):
        create_document_intelligence_app(runtime_config=config, auth_config=APIAuthConfig(), snapshot_at=NOW)

