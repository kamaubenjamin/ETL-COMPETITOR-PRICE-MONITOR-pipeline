import ast
from pathlib import Path


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield f"{'.' * node.level}{node.module}"


def test_api_platform_runtime_imports_are_limited_to_approved_entrypoints():
    approved = {
        Path("src/api/document_intelligence/app.py"),
        Path("src/api/document_intelligence/auth.py"),
        Path("src/api/document_intelligence/config.py"),
    }
    actual = {
        path
        for path in Path("src/api").rglob("*.py")
        if any(module == "src.platform_runtime" or module.startswith("src.platform_runtime.") for module in _imports(path))
    }
    assert actual == approved


def test_core_boundaries_do_not_reverse_import_outer_layers():
    forbidden = ("src.platform_runtime", "src.api", "src.ui")
    for package in ("security", "document_state", "workflow_runtime/query_facade"):
        for path in (Path("src") / package).rglob("*.py"):
            imports = tuple(_imports(path))
            assert not any(
                module == prefix or module.startswith(f"{prefix}.")
                for module in imports
                for prefix in forbidden
            ), path


def test_platform_runtime_has_no_forbidden_outer_or_service_imports():
    forbidden = (
        "src.api",
        "src.ui",
        "src.telemetry",
        "src.storage",
        "streamlit",
        "requests",
        "supabase",
        "openai",
    )
    for path in Path("src/platform_runtime").rglob("*.py"):
        imports = tuple(_imports(path))
        assert not any(
            module == prefix or module.startswith(f"{prefix}.")
            for module in imports
            for prefix in forbidden
        ), path

