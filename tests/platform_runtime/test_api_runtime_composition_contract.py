import ast
from pathlib import Path


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield f"{'.' * node.level}{node.module}"


def test_api_may_import_platform_runtime_but_core_boundaries_do_not_reverse_import():
    api_imports = set(_imports(Path("src/api/document_intelligence/app.py")))
    assert "src.platform_runtime" in api_imports
    for package in ("platform_runtime", "security", "document_state", "workflow_runtime/query_facade"):
        for path in (Path("src") / package).rglob("*.py"):
            imports = set(_imports(path))
            assert not any(module == "src.api" or module.startswith("src.api.") for module in imports), path


def test_streamlit_source_is_not_modified_by_api_runtime_activation():
    for path in Path("src/ui/streamlit").rglob("*.py"):
        assert not any(
            module == "src.platform_runtime" or module.startswith("src.platform_runtime.")
            for module in _imports(path)
        ), path

