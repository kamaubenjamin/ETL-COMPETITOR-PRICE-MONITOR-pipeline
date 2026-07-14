import pytest

from src.api.document_intelligence.auth import create_runtime_auth_composition
from src.api.document_intelligence.config import APIAuthMode, api_auth_config_from_runtime
from src.platform_runtime import AuthConfig, RuntimeValidationError
from src.security.providers import LocalIdentityProvider


def test_disabled_runtime_auth_maps_to_existing_disabled_api_behavior():
    mapped = api_auth_config_from_runtime(AuthConfig("disabled"))
    composed = create_runtime_auth_composition(AuthConfig("disabled"))
    assert mapped.mode == APIAuthMode.DISABLED
    assert composed.config.enabled is False
    assert composed.identity_provider is None


def test_local_demo_runtime_auth_maps_to_existing_local_identity_behavior():
    config = AuthConfig("local_demo", identity_provider="local_demo", identity_provider_available=True)
    composed = create_runtime_auth_composition(config)
    assert composed.config.mode == APIAuthMode.LOCAL_DEMO
    assert isinstance(composed.identity_provider, LocalIdentityProvider)
    assert composed.identity_provider.resolve("viewer").resolved is True


@pytest.mark.parametrize("mode", ["authenticated", "production"])
def test_unimplemented_runtime_auth_modes_fail_closed(mode):
    config = AuthConfig(mode, identity_provider="external", identity_provider_available=True)
    with pytest.raises(RuntimeValidationError) as raised:
        create_runtime_auth_composition(config)
    assert raised.value.code.value == "composition_failed"
    assert raised.value.field == "auth"

