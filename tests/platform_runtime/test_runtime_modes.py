import pytest

from src.platform_runtime import (
    AuthMode,
    BackendMode,
    RuntimeMode,
    allowed_auth_modes,
    allowed_backend_modes,
    is_local_like,
    is_production_like,
)


def test_runtime_backend_and_auth_modes_are_fixed_and_deterministic():
    assert tuple(item.value for item in RuntimeMode) == (
        "local", "test", "demo", "local_api_auth", "pilot", "production"
    )
    assert tuple(item.value for item in BackendMode) == (
        "in_memory", "sqlite", "future_postgres"
    )
    assert tuple(item.value for item in AuthMode) == (
        "disabled", "local_demo", "authenticated", "production"
    )


def test_runtime_mode_helpers_return_immutable_explicit_sets():
    assert is_local_like("local")
    assert is_local_like(RuntimeMode.DEMO)
    assert is_production_like("pilot")
    assert is_production_like(RuntimeMode.PRODUCTION)
    assert allowed_backend_modes("pilot") == frozenset({BackendMode.SQLITE})
    assert allowed_auth_modes("production") == frozenset({AuthMode.PRODUCTION})


def test_runtime_mode_helpers_reject_unknown_values():
    with pytest.raises(ValueError, match="runtime mode"):
        allowed_backend_modes("fallback")

