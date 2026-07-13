import ast
from pathlib import Path


SECURITY_ROOT = Path("src/security")
FORBIDDEN_PREFIXES = (
    "src.api",
    "src.ui",
    "src.document_state",
    "src.workflow_runtime",
    "src.storage",
    "src.telemetry",
    "fastapi",
    "streamlit",
    "sqlalchemy",
    "supabase",
)


def imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_security_package_has_no_forbidden_imports():
    violations = []
    for path in SECURITY_ROOT.rglob("*.py"):
        for imported in imports(path):
            if imported.startswith(FORBIDDEN_PREFIXES):
                violations.append(f"{path}:{imported}")
    assert violations == []


def test_phase2_does_not_create_integration_modules():
    assert not (SECURITY_ROOT / "api.py").exists()
    assert not (SECURITY_ROOT / "streamlit.py").exists()
    assert not (SECURITY_ROOT / "repositories.py").exists()
