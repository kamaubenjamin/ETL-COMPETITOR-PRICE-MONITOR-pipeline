import ast
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "export_runtime"
PHASE_THREE = {"queries.py", "repositories.py", "repository_errors.py", "store.py"}
FORBIDDEN = {
    "api",
    "document_state",
    "platform_runtime",
    "review_runtime",
    "security",
    "storage",
    "telemetry",
    "ui",
    "workflow_runtime",
}


def imports_for(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield 0, alias.name
        elif isinstance(node, ast.ImportFrom):
            yield node.level, node.module or ""


def test_phase_three_modules_import_only_standard_library_and_package_local_modules():
    violations = []
    for name in PHASE_THREE:
        for level, module in imports_for(PACKAGE / name):
            root = module.split(".", 1)[0]
            if level:
                continue
            if root not in sys.stdlib_module_names:
                violations.append((name, module))
            if root in FORBIDDEN or module.startswith("src."):
                violations.append((name, module))
    assert violations == []


def test_phase_three_adds_no_persistence_adapter_service_or_io_surface():
    names = {path.name for path in PACKAGE.glob("*.py")}
    assert "service.py" not in names
    assert "repositories_sqlite.py" not in names
    assert not (PACKAGE / "adapters").exists()
    for name in PHASE_THREE:
        source = (PACKAGE / name).read_text(encoding="utf-8-sig").lower()
        assert "sqlite" not in source
        assert "requests" not in source
        assert "open(" not in source


def test_existing_source_still_does_not_import_export_runtime():
    violations = []
    for path in (ROOT / "src").rglob("*.py"):
        if PACKAGE in path.parents:
            continue
        for _level, module in imports_for(path):
            if module == "export_runtime" or module.startswith("export_runtime.") or module.startswith("src.export_runtime"):
                violations.append(str(path.relative_to(ROOT)))
    assert violations == []

