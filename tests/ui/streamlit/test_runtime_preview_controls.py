import inspect

from src.ui.streamlit.data_providers import DEFAULT_PROVIDER_MODE
from src.ui.streamlit.runtime_preview import (
    PREVIEW_AUTH_MODES,
    PREVIEW_BACKENDS,
    PREVIEW_RUNTIME_MODES,
    RuntimePreviewSelection,
)


def test_preview_choices_are_fixed_and_local_preview_remains_default():
    assert DEFAULT_PROVIDER_MODE == "local_preview"
    assert PREVIEW_RUNTIME_MODES == ("local", "test", "demo", "local_api_auth")
    assert PREVIEW_BACKENDS == ("api_default", "in_memory", "sqlite")
    assert PREVIEW_AUTH_MODES == ("disabled", "local_demo")


def test_runtime_controls_are_api_only_and_clearly_non_authoritative():
    import src.ui.streamlit.document_intelligence_app as app_module

    source = inspect.getsource(app_module)
    assert 'provider_mode == "api_preview"' in source
    assert "Runtime preview (non-authoritative)" in source
    assert "Runtime composition remains API-owned" in source
    assert "runtime_preview_mismatch" in source


def test_safe_preview_summary_contains_labels_not_runtime_configuration():
    summary = RuntimePreviewSelection("demo", "sqlite", "local_demo").to_safe_dict()
    assert summary == {
        "runtime_mode_label": "demo",
        "backend_label": "sqlite",
        "auth_mode_label": "local_demo",
        "authoritative": False,
        "source_of_truth": "document_intelligence_api",
    }

