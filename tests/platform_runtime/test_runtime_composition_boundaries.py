import ast
from pathlib import Path


ROOT = Path("src/platform_runtime")
INTEGRATION_FILES = {"composition.py", "document_state.py", "lifecycle.py", "query_facade.py", "writers.py"}
ALLOWED_ROOTS = {"__future__", "dataclasses", "typing", "src.document_state", "src.workflow_runtime.query_facade"}


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield f"{'.' * node.level}{node.module}"


def test_composition_modules_import_only_approved_public_boundaries():
    for name in INTEGRATION_FILES:
        for module in _imports(ROOT / name):
            if module.startswith("."):
                continue
            assert any(module == root or module.startswith(f"{root}.") for root in ALLOWED_ROOTS), (name, module)


def test_core_packages_do_not_import_platform_runtime():
    for package in ("document_state", "workflow_runtime", "security", "api", "ui"):
        for path in (Path("src") / package).rglob("*.py"):
            assert not any(
                module == "src.platform_runtime" or module.startswith("src.platform_runtime.")
                for module in _imports(path)
            ), path


def test_composition_has_no_forbidden_integration_imports():
    imported = {
        module
        for name in INTEGRATION_FILES
        for module in _imports(ROOT / name)
        if not module.startswith(".")
    }
    for forbidden in ("src.api", "src.ui", "streamlit", "dashboard", "telemetry", "src.storage"):
        assert not any(module == forbidden or module.startswith(f"{forbidden}.") for module in imported)
