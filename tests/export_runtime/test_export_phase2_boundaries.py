import ast
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "export_runtime"
PHASE_TWO_MODULES = {"builder.py", "fingerprints.py", "normalization.py", "policy.py"}
FORBIDDEN = {
    "api",
    "document_state",
    "platform_runtime",
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


def test_phase_two_modules_use_only_standard_library_and_package_local_imports():
    violations = []
    for name in PHASE_TWO_MODULES:
        for level, module in imports_for(PACKAGE / name):
            root = module.split(".", 1)[0]
            if level:
                continue
            if root not in sys.stdlib_module_names:
                violations.append((name, module))
            if root in FORBIDDEN or module.startswith("src."):
                violations.append((name, module))
    assert violations == []


def test_phase_two_modules_remain_free_of_service_adapter_and_io_dependencies():
    for name in PHASE_TWO_MODULES:
        source = (PACKAGE / name).read_text(encoding="utf-8-sig")
        assert "open(" not in source
        assert "sqlite" not in source.lower()
        assert "requests" not in source.lower()
