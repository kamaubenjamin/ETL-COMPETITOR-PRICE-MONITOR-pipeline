import inspect

import pytest

from src.ui.streamlit.runtime_preview import RuntimePreviewSelection


def test_preview_labels_cannot_enable_production():
    with pytest.raises(ValueError):
        RuntimePreviewSelection(runtime_mode="production")


def test_streamlit_source_contains_no_runtime_construction_or_authorization_policy():
    import src.ui.streamlit.document_intelligence_app as app_module
    import src.ui.streamlit.runtime_preview as preview_module

    source = (inspect.getsource(app_module) + inspect.getsource(preview_module)).lower()
    for forbidden in (
        "compose_runtime(",
        "runtimecomposition(",
        "documentstatecomposition(",
        "lifecycleadvancementservice(",
        "permissionguard(",
        "tenant_id =",
    ):
        assert forbidden not in source
    assert "source_of_truth" in source
    assert "document_intelligence_api" in source
