import json

import pytest

from src.platform_runtime import (
    ApiConfig,
    ApiRuntimeMode,
    AuthConfig,
    BackendConfig,
    RuntimeConfig,
    RuntimeValidationError,
    StreamlitConfig,
)


def local_config(*, sqlite_path=None):
    backend = BackendConfig("sqlite", sqlite_path=sqlite_path) if sqlite_path else BackendConfig("in_memory")
    return RuntimeConfig(
        "local",
        backend,
        AuthConfig("disabled"),
        ApiConfig("read_only_unguarded"),
        StreamlitConfig("local_preview"),
    )


def test_runtime_config_is_frozen_and_normalizes_string_modes():
    config = local_config()
    assert config.runtime_mode.value == "local"
    assert config.backend.mode.value == "in_memory"
    with pytest.raises(AttributeError):
        config.runtime_mode = "production"


def test_redacted_config_serialization_is_json_safe_and_hides_paths_and_references():
    path = "C:/private/runtime/state.sqlite3"
    reference = "vault://private/identity/provider"
    config = RuntimeConfig(
        "pilot",
        BackendConfig("sqlite", sqlite_path=path),
        AuthConfig(
            "authenticated",
            identity_provider="external",
            identity_provider_available=True,
            identity_provider_reference=reference,
        ),
        ApiConfig("read_only_guarded"),
        StreamlitConfig("api_preview"),
    )
    serialized = json.dumps(config.to_redacted_dict(), sort_keys=True)
    assert path not in serialized
    assert reference not in serialized
    assert '"sqlite_path_configured": true' in serialized
    assert '"identity_provider_reference_configured": true' in serialized
    assert path not in repr(config.backend)
    assert reference not in repr(config.auth)


@pytest.mark.parametrize(
    ("factory", "field"),
    [
        (lambda: BackendConfig("unknown"), "backend"),
        (lambda: AuthConfig("unknown"), "auth"),
        (lambda: ApiConfig("unknown"), "api"),
        (lambda: StreamlitConfig("unknown"), "streamlit"),
    ],
)
def test_invalid_config_values_raise_safe_contract_errors(factory, field):
    with pytest.raises(RuntimeValidationError) as raised:
        factory()
    assert raised.value.code.value == "invalid_config"
    assert raised.value.field == field


def test_config_construction_does_not_read_or_mutate_environment(monkeypatch):
    monkeypatch.setenv("IDP_RUNTIME_MODE", "production")
    before = dict(__import__("os").environ)
    assert local_config().runtime_mode.value == "local"
    assert dict(__import__("os").environ) == before

