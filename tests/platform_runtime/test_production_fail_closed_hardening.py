import pytest

from src.platform_runtime import (
    ApiConfig,
    AuthConfig,
    BackendConfig,
    RuntimeConfig,
    RuntimeValidationError,
    StreamlitConfig,
    assert_runtime_config_valid,
    validate_runtime_config,
)


def _config(mode, backend, auth, *, api="read_only_guarded", streamlit="api_preview"):
    return RuntimeConfig(mode, backend, auth, ApiConfig(api), StreamlitConfig(streamlit))


def _external(mode="production", *, available=True):
    return AuthConfig(
        mode,
        identity_provider="external",
        identity_provider_available=available,
        identity_provider_reference="secret://identity/provider",
    )


@pytest.mark.parametrize(
    "config",
    [
        _config("production", BackendConfig("in_memory"), _external()),
        _config("production", BackendConfig("sqlite", sqlite_path="C:/private/prod.sqlite3"), _external()),
        _config("production", BackendConfig("future_postgres"), AuthConfig("disabled")),
        _config(
            "production",
            BackendConfig("future_postgres"),
            AuthConfig("local_demo", identity_provider="local_demo", identity_provider_available=True),
        ),
        _config("production", BackendConfig("future_postgres"), _external("authenticated")),
        _config("production", BackendConfig("future_postgres"), _external("production")),
        _config("production", None, _external()),
        _config("production", BackendConfig("future_postgres"), None),
        _config("production", BackendConfig("future_postgres"), _external(available=False)),
    ],
)
def test_every_current_production_combination_fails_closed(config):
    result = validate_runtime_config(config)
    assert result.valid is False
    assert "production_not_available" in {error.code.value for error in result.errors}
    with pytest.raises(RuntimeValidationError):
        assert_runtime_config_valid(config)


@pytest.mark.parametrize("mode", ["local", "test", "demo", "local_api_auth", "pilot"])
def test_future_postgres_is_deferred_in_every_nonproduction_mode(mode):
    auth = (
        AuthConfig("disabled")
        if mode in {"local", "test"}
        else AuthConfig("local_demo", identity_provider="local_demo", identity_provider_available=True)
        if mode in {"demo", "local_api_auth"}
        else _external("authenticated")
    )
    config = _config(mode, BackendConfig("future_postgres"), auth)
    codes = {error.code.value for error in validate_runtime_config(config).errors}
    assert "backend_deferred" in codes


def test_sqlite_without_explicit_path_fails_with_stable_code():
    config = _config(
        "local",
        BackendConfig("sqlite"),
        AuthConfig("disabled"),
        api="read_only_unguarded",
        streamlit="local_preview",
    )
    assert [error.code.value for error in validate_runtime_config(config).errors] == [
        "sqlite_path_required"
    ]

