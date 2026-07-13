import inspect

from src.ui.streamlit.api_client import AUTH_PREVIEW_IDENTITIES
from src.ui.streamlit.data_providers import DEFAULT_PROVIDER_MODE


def test_auth_preview_choices_are_fixed_and_local_preview_remains_default():
    assert DEFAULT_PROVIDER_MODE == "local_preview"
    assert AUTH_PREVIEW_IDENTITIES == (
        "unspecified",
        "anonymous",
        "viewer",
        "reviewer",
        "tenant-admin",
        "platform-admin",
        "service-account",
    )


def test_streamlit_auth_preview_is_api_only_and_not_authoritative():
    import src.ui.streamlit.document_intelligence_app as app_module

    source = inspect.getsource(app_module)
    assert 'provider_mode == "api_preview"' in source
    assert "auth_preview_identity=" in source
    assert "src.security" not in source
    assert "document_state" not in source
    assert "query_facade" not in source
    assert "cross-tenant access is disabled by default" in source

