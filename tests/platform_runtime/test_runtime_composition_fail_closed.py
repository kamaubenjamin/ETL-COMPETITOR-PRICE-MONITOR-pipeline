import json

import pytest

from src.platform_runtime import (
    ApiConfig,
    AuthConfig,
    BackendConfig,
    RuntimeConfig,
    RuntimeValidationError,
    StreamlitConfig,
    compose_runtime,
)


SNAPSHOT_AT = "2026-07-14T11:00:00+00:00"


def _production(backend):
    return RuntimeConfig(
        "production",
        backend,
        AuthConfig(
            "production",
            identity_provider="external",
            identity_provider_available=True,
            identity_provider_reference="secret://identity/provider",
        ),
        ApiConfig("read_only_guarded"),
        StreamlitConfig("api_preview"),
    )


@pytest.mark.parametrize(
    "config",
    [
        _production(BackendConfig("future_postgres")),
        _production(BackendConfig("in_memory")),
        _production(BackendConfig("sqlite", sqlite_path="private/runtime.sqlite3")),
        RuntimeConfig(
            "local",
            BackendConfig("sqlite"),
            AuthConfig("disabled"),
            ApiConfig("read_only_unguarded"),
            StreamlitConfig("local_preview"),
        ),
    ],
)
def test_unsupported_backends_and_production_fail_closed(config):
    with pytest.raises(RuntimeValidationError) as raised:
        compose_runtime(config, snapshot_at=SNAPSHOT_AT)
    payload = json.dumps(raised.value.to_dict())
    assert "private/runtime.sqlite3" not in payload
    assert "secret://identity/provider" not in payload


def test_invalid_config_is_rejected_before_resource_construction(monkeypatch):
    called = False

    def unexpected(_config):
        nonlocal called
        called = True
        raise AssertionError("resource construction must not run")

    monkeypatch.setattr("src.platform_runtime.composition.compose_runtime_document_state", unexpected)
    with pytest.raises(RuntimeValidationError):
        compose_runtime(_production(BackendConfig("future_postgres")), snapshot_at=SNAPSHOT_AT)
    assert called is False


def test_invalid_snapshot_returns_stable_safe_composition_error():
    config = RuntimeConfig(
        "local",
        BackendConfig("in_memory"),
        AuthConfig("disabled"),
        ApiConfig("read_only_unguarded"),
        StreamlitConfig("local_preview"),
    )
    with pytest.raises(RuntimeValidationError) as raised:
        compose_runtime(config, snapshot_at="not-a-timestamp")
    assert raised.value.code.value == "composition_failed"
    assert raised.value.to_dict() == {
        "code": "composition_failed",
        "field": None,
        "message": "Runtime composition could not be completed.",
    }

