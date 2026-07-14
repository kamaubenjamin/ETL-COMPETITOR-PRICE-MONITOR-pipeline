import ast
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "export_runtime"
PHASE_FOUR = {
    "service.py",
    "commands.py",
    "audit.py",
    "lifecycle.py",
    "service_errors.py",
    "adapters/placeholder.py",
}
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


def test_phase_four_modules_use_only_standard_library_and_package_local_imports():
    violations = []
    for relative in PHASE_FOUR:
        for level, module in imports_for(PACKAGE / relative):
            root = module.split(".", 1)[0]
            if level:
                continue
            if root not in sys.stdlib_module_names:
                violations.append((relative, module))
            if root in FORBIDDEN or module.startswith("src."):
                violations.append((relative, module))
    assert violations == []


def test_phase_four_has_no_network_file_database_or_real_adapter_imports():
    for relative in PHASE_FOUR:
        source = (PACKAGE / relative).read_text(encoding="utf-8-sig").lower()
        for forbidden in ("requests", "httpx", "urllib", "socket", "sqlite", "open(", "subprocess", "boto", "sap", "oracle"):
            assert forbidden not in source


def test_existing_source_modules_still_do_not_import_export_runtime():
    violations = []
    for path in (ROOT / "src").rglob("*.py"):
        if PACKAGE in path.parents:
            continue
        for _level, module in imports_for(path):
            if module == "export_runtime" or module.startswith("export_runtime.") or module.startswith("src.export_runtime"):
                violations.append(str(path.relative_to(ROOT)))
    assert violations == []

