import ast
from pathlib import Path

import pytest

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.providers import FacadeDocumentIntelligenceProvider, facade_provider
from src.platform_runtime import (
    ApiConfig,
    AuthConfig,
    BackendConfig,
    RuntimeComposition,
    RuntimeConfig,
    RuntimeValidationError,
    StreamlitConfig,
    compose_runtime,
)


NOW = "2026-07-14T15:00:00+00:00"


def _local():
    return RuntimeConfig(
        "local",
        BackendConfig("in_memory"),
        AuthConfig("disabled"),
        ApiConfig("read_only_unguarded"),
        StreamlitConfig("local_preview"),
    )


def _production():
    return RuntimeConfig(
        "production",
        BackendConfig("future_postgres"),
        AuthConfig("production", identity_provider="external", identity_provider_available=True),
        ApiConfig("read_only_guarded"),
        StreamlitConfig("api_preview"),
    )


def _forge_composition(valid, invalid_config):
    forged = object.__new__(RuntimeComposition)
    for field in ("document_state", "lifecycle", "writers", "query_facade"):
        object.__setattr__(forged, field, getattr(valid, field))
    object.__setattr__(forged, "runtime_config", invalid_config)
    return forged


def test_precomposed_runtime_config_is_revalidated_before_app_creation(monkeypatch):
    valid = compose_runtime(_local(), snapshot_at=NOW)
    forged = _forge_composition(valid, _production())
    called = False

    def unexpected(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("FastAPI must not be constructed")

    monkeypatch.setattr("src.api.document_intelligence.app.FastAPI", unexpected)
    with pytest.raises(RuntimeValidationError):
        create_document_intelligence_app(runtime_composition=forged)
    assert called is False


def test_composed_provider_is_app_scoped_and_compatibility_singleton_is_unchanged():
    default_app = create_document_intelligence_app()
    composed_app = create_document_intelligence_app(runtime_config=_local(), snapshot_at=NOW)
    assert default_app.state.document_intelligence_provider is facade_provider
    assert isinstance(composed_app.state.document_intelligence_provider, FacadeDocumentIntelligenceProvider)
    assert composed_app.state.document_intelligence_provider is not facade_provider


def test_every_data_router_resolves_provider_from_request_scope():
    router_dir = Path("src/api/document_intelligence/routers")
    for name in ("documents.py", "validation.py", "matching.py", "reviews.py", "workflows.py", "audit.py"):
        path = router_dir / name
        source = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(source, filename=str(path))
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module == "providers"
            for alias in node.names
        }
        assert "local_provider" not in source
        assert "get_document_intelligence_provider" in source

