import ast
from pathlib import Path


SECURITY_ROOT = Path("src/security")


FORBIDDEN_PARTS = {
    "api",
    "document_engine",
    "document_state",
    "entity_runtime",
    "fastapi",
    "flowsync",
    "matching_runtime",
    "persistence",
    "review_runtime",
    "sqlite",
    "storage",
    "streamlit",
    "telemetry",
    "transform",
    "transforms",
    "ui",
    "workflow_runtime",
    "writers",
}


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module


def test_security_package_has_no_forbidden_imports():
    for path in SECURITY_ROOT.rglob("*.py"):
        for module in _imports(path):
            parts = {part.lower() for part in module.split(".")}
            assert not parts & FORBIDDEN_PARTS, f"{path} imports forbidden module {module}"


def test_existing_production_modules_do_not_import_security_yet():
    for path in Path("src").rglob("*.py"):
        if SECURITY_ROOT in path.parents:
            continue
        assert all(not module.startswith("src.security") for module in _imports(path)), path


def test_security_package_contains_no_provider_or_guard_integration():
    assert not (SECURITY_ROOT / "guards.py").exists()
    assert not (SECURITY_ROOT / "providers").exists()

