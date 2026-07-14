import ast
import json
from pathlib import Path

import pytest

from src.ui.streamlit.runtime_preview import RuntimePreviewSelection, runtime_preview_mismatch


@pytest.mark.parametrize(
    "arguments",
    [
        {"runtime_mode": "production"},
        {"backend": "C:/private/runtime.sqlite3"},
        {"auth_mode": "secret-token"},
    ],
)
def test_preview_rejects_raw_or_unsupported_configuration_values(arguments):
    with pytest.raises(ValueError):
        RuntimePreviewSelection(**arguments)


def test_preview_summary_and_mismatch_messages_never_expose_sensitive_values():
    selection = RuntimePreviewSelection("local_api_auth", "sqlite", "disabled")
    summary = json.dumps(selection.to_safe_dict())
    message = runtime_preview_mismatch(selection, auth_preview_identity="viewer")
    for forbidden in ("C:/", "sqlite3", "secret", "token", "claim", "credential"):
        assert forbidden.lower() not in (summary + str(message)).lower()


def test_streamlit_runtime_preview_has_no_forbidden_runtime_imports():
    forbidden = {
        "src.platform_runtime",
        "src.document_state",
        "src.workflow_runtime.query_facade",
        "src.security",
    }
    for relative in (
        "src/ui/streamlit/document_intelligence_app.py",
        "src/ui/streamlit/runtime_preview.py",
    ):
        path = Path(relative)
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert not any(
            module == prefix or module.startswith(f"{prefix}.")
            for module in modules
            for prefix in forbidden
        )


def test_preview_mismatch_guidance_does_not_make_authorization_decisions():
    disabled = RuntimePreviewSelection(auth_mode="disabled")
    local_demo = RuntimePreviewSelection(auth_mode="local_demo")
    assert "API remains authoritative" in runtime_preview_mismatch(
        disabled, auth_preview_identity="viewer"
    )
    assert "API may require authentication" in runtime_preview_mismatch(
        local_demo, auth_preview_identity="unspecified"
    )
    assert runtime_preview_mismatch(local_demo, auth_preview_identity="reviewer") is None

