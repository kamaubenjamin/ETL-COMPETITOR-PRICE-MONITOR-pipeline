import ast
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "upload_runtime"
PHASE_THREE = {"activation.py", "processing.py", "staging.py", "integration.py", "activation_errors.py"}


def imports_for(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield 0, alias.name
        elif isinstance(node, ast.ImportFrom):
            yield node.level, node.module or ""


def test_phase_three_upload_modules_use_only_standard_library_and_package_local_imports():
    violations = []
    for name in PHASE_THREE:
        for level, module in imports_for(PACKAGE / name):
            if level:
                continue
            if module.split(".", 1)[0] not in sys.stdlib_module_names or module.startswith("src."):
                violations.append((name, module))
    assert violations == []


def test_phase_three_contains_no_io_runtime_writer_export_ai_or_external_service_imports():
    source = "\n".join((PACKAGE / name).read_text(encoding="utf-8-sig").lower() for name in PHASE_THREE)
    for forbidden in (
        "fastapi", "streamlit", "sqlite", "requests", "httpx", "subprocess",
        "open(", "write_bytes", "read_bytes", "openai", "boto", "oracle",
    ):
        assert forbidden not in source
