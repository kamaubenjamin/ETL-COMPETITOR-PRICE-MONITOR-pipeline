import ast
from pathlib import Path


ROOT = Path("src/platform_runtime")
STANDARD_ROOTS = {"__future__", "dataclasses", "enum", "typing"}
APPROVED_INTEGRATION_ROOTS = {"src.document_state", "src.workflow_runtime.query_facade"}


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield f"{'.' * node.level}{node.module}"


def test_platform_runtime_core_imports_only_standard_or_package_local_modules():
    for path in ROOT.rglob("*.py"):
        if path.name in {"composition.py", "document_state.py", "lifecycle.py", "query_facade.py", "writers.py"}:
            continue
        for module in _imports(path):
            if module.startswith("."):
                continue
            assert module.split(".")[0] in STANDARD_ROOTS, f"{path} imports {module}"


def test_only_approved_api_composition_module_imports_platform_runtime():
    approved = {
        Path("src/api/document_intelligence/app.py"),
        Path("src/api/document_intelligence/auth.py"),
        Path("src/api/document_intelligence/config.py"),
    }
    for path in Path("src").rglob("*.py"):
        if ROOT in path.parents:
            continue
        imports_runtime = any(
            module == "src.platform_runtime" or module.startswith("src.platform_runtime.")
            for module in _imports(path)
        )
        assert not imports_runtime or path in approved, path


def test_platform_runtime_integration_imports_only_approved_public_boundaries():
    for name in ("composition.py", "document_state.py", "lifecycle.py", "query_facade.py", "writers.py"):
        for module in _imports(ROOT / name):
            if module.startswith(".") or module.split(".")[0] in STANDARD_ROOTS:
                continue
            assert any(module == root or module.startswith(f"{root}.") for root in APPROVED_INTEGRATION_ROOTS), module


def test_platform_runtime_has_no_api_or_security_composition_modules_yet():
    for name in ("api.py", "security.py", "streamlit.py"):
        assert not (ROOT / name).exists()


def test_platform_runtime_has_no_environment_or_import_time_io():
    source = "\n".join(path.read_text(encoding="utf-8-sig") for path in ROOT.rglob("*.py"))
    for forbidden in ("os.environ", "os.getenv", "open(", "urlopen", "sqlite3", "requests"):
        assert forbidden not in source
