import ast
from pathlib import Path


ROOT = Path("src/platform_runtime")
STANDARD_ROOTS = {"__future__", "dataclasses", "enum", "typing"}


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield f"{'.' * node.level}{node.module}"


def test_platform_runtime_phase_one_imports_only_standard_or_package_local_modules():
    for path in ROOT.rglob("*.py"):
        for module in _imports(path):
            if module.startswith("."):
                continue
            assert module.split(".")[0] in STANDARD_ROOTS, f"{path} imports {module}"


def test_existing_production_modules_do_not_import_platform_runtime_yet():
    for path in Path("src").rglob("*.py"):
        if ROOT in path.parents:
            continue
        assert not any(
            module == "src.platform_runtime" or module.startswith("src.platform_runtime.")
            for module in _imports(path)
        ), path


def test_platform_runtime_has_no_composition_or_integration_modules_yet():
    for name in ("api.py", "composition.py", "document_state.py", "security.py"):
        assert not (ROOT / name).exists()


def test_platform_runtime_has_no_environment_or_import_time_io():
    source = "\n".join(path.read_text(encoding="utf-8-sig") for path in ROOT.rglob("*.py"))
    for forbidden in ("os.environ", "os.getenv", "open(", "urlopen", "sqlite3", "requests"):
        assert forbidden not in source

