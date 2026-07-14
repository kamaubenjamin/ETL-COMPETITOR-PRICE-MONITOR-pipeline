import inspect

import pytest

from src.api.document_intelligence.auth import create_runtime_auth_composition
from src.platform_runtime import AuthConfig, RuntimeValidationError


@pytest.mark.parametrize("mode", ["authenticated", "production"])
def test_placeholder_auth_never_constructs_local_identity_provider(monkeypatch, mode):
    called = False

    def unexpected(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("local identity must not be constructed")

    monkeypatch.setattr("src.api.document_intelligence.auth.create_local_demo_provider", unexpected)
    config = AuthConfig(mode, identity_provider="external", identity_provider_available=True)
    with pytest.raises(RuntimeValidationError):
        create_runtime_auth_composition(config)
    assert called is False


def test_runtime_auth_and_app_composition_do_not_infer_tokens_or_environment():
    import src.api.document_intelligence.app as app_module
    import src.api.document_intelligence.auth as auth_module
    import src.api.document_intelligence.config as config_module

    source = "\n".join(inspect.getsource(module) for module in (app_module, auth_module, config_module))
    for forbidden in ("os.environ", "os.getenv", "environ.get", "token=", "password="):
        assert forbidden not in source

