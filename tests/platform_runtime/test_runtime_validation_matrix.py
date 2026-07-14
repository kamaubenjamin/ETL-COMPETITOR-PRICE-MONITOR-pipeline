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


def config(mode, backend, auth, *, api=None, streamlit=None):
    guarded = auth is not None and auth.mode.value != "disabled"
    return RuntimeConfig(
        mode,
        backend,
        auth,
        ApiConfig(api or ("read_only_guarded" if guarded else "read_only_unguarded")),
        StreamlitConfig(streamlit or ("local_preview" if mode in {"local", "test"} else "api_preview")),
    )


def disabled_auth():
    return AuthConfig("disabled")


def local_demo_auth():
    return AuthConfig("local_demo", identity_provider="local_demo", identity_provider_available=True)


def external_auth(mode="authenticated", *, available=True):
    return AuthConfig(mode, identity_provider="external", identity_provider_available=available)


@pytest.mark.parametrize(
    "runtime_config",
    [
        config("local", BackendConfig("in_memory"), disabled_auth()),
        config("local", BackendConfig("sqlite", sqlite_path="local.sqlite3"), disabled_auth()),
        config("test", BackendConfig("in_memory"), disabled_auth()),
        config("test", BackendConfig("sqlite", sqlite_path="test.sqlite3"), local_demo_auth()),
        config("demo", BackendConfig("sqlite", sqlite_path="demo.sqlite3"), local_demo_auth()),
        config("local_api_auth", BackendConfig("in_memory"), local_demo_auth()),
        config("local_api_auth", BackendConfig("sqlite", sqlite_path="auth.sqlite3"), local_demo_auth()),
        config("pilot", BackendConfig("sqlite", sqlite_path="pilot.sqlite3"), external_auth()),
    ],
)
def test_supported_runtime_matrix_combinations_are_valid(runtime_config):
    result = validate_runtime_config(runtime_config)
    assert result.valid, result.to_dict()
    assert assert_runtime_config_valid(runtime_config) is runtime_config


@pytest.mark.parametrize(
    ("runtime_config", "expected_code"),
    [
        (config("pilot", BackendConfig("in_memory"), external_auth()), "backend_not_allowed"),
        (config("production", BackendConfig("in_memory"), external_auth("production")), "backend_not_allowed"),
        (config("production", BackendConfig("sqlite", sqlite_path="prod.sqlite3"), external_auth("production")), "backend_not_allowed"),
        (config("production", BackendConfig("future_postgres"), disabled_auth()), "auth_not_allowed"),
        (config("production", BackendConfig("future_postgres"), local_demo_auth()), "auth_not_allowed"),
        (config("production", BackendConfig("future_postgres"), external_auth("authenticated")), "auth_not_allowed"),
        (config("production", BackendConfig("future_postgres"), external_auth("production", available=False)), "identity_provider_required"),
        (config("production", None, external_auth("production")), "backend_required"),
        (config("production", BackendConfig("future_postgres"), None, api="read_only_guarded"), "auth_required"),
        (config("local", BackendConfig("future_postgres"), disabled_auth()), "backend_deferred"),
        (config("local", BackendConfig("sqlite"), disabled_auth()), "sqlite_path_required"),
        (config("local", BackendConfig("sqlite", sqlite_path=":memory:"), disabled_auth()), "sqlite_path_invalid"),
        (config("local", BackendConfig("in_memory"), external_auth()), "auth_not_allowed"),
        (config("local_api_auth", BackendConfig("in_memory"), disabled_auth(), api="read_only_guarded"), "auth_not_allowed"),
        (config("demo", BackendConfig("in_memory"), local_demo_auth(), api="read_only_unguarded"), "api_mode_not_allowed"),
        (config("pilot", BackendConfig("sqlite", sqlite_path="pilot.sqlite3"), external_auth(), streamlit="local_preview"), "streamlit_mode_not_allowed"),
    ],
)
def test_unsafe_runtime_matrix_combinations_fail_closed(runtime_config, expected_code):
    result = validate_runtime_config(runtime_config)
    assert not result.valid
    assert expected_code in {error.code.value for error in result.errors}


def test_authenticated_placeholder_requires_explicit_available_external_provider():
    runtime_config = config(
        "pilot",
        BackendConfig("sqlite", sqlite_path="pilot.sqlite3"),
        external_auth(available=False),
    )
    assert "identity_provider_required" in {
        error.code.value for error in validate_runtime_config(runtime_config).errors
    }


def test_production_always_reports_unavailable_until_adapters_exist():
    runtime_config = config(
        "production",
        BackendConfig("future_postgres"),
        external_auth("production"),
    )
    codes = [error.code.value for error in validate_runtime_config(runtime_config).errors]
    assert "backend_deferred" in codes
    assert "production_not_available" in codes
    with pytest.raises(RuntimeValidationError) as raised:
        assert_runtime_config_valid(runtime_config)
    assert raised.value.code.value == codes[0]


def test_validation_result_error_order_is_deterministic():
    runtime_config = config(
        "production",
        None,
        None,
        api="read_only_unguarded",
        streamlit="local_preview",
    )
    first = validate_runtime_config(runtime_config).to_dict()
    second = validate_runtime_config(runtime_config).to_dict()
    assert first == second

