import ast
from pathlib import Path

import src.workflow_runtime.query_facade as query_facade


FACADE_ROOT = Path(query_facade.__file__).parent
FORBIDDEN_PARTS = {
    "api", "competitor", "database", "document_engine", "entity_runtime",
    "flowsync", "llm", "matching_runtime", "ocr", "review_runtime",
    "storage", "streamlit", "telemetry", "transform", "transforms", "ui",
}


def _absolute_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imports.add(node.module)
    return imports


def test_query_facade_package_has_no_forbidden_imports():
    for path in FACADE_ROOT.rglob("*.py"):
        for module in _absolute_imports(path):
            parts = {part.lower() for part in module.split(".")}
            assert not parts & FORBIDDEN_PARTS, f"forbidden import {module!r} in {path}"


def test_query_facade_has_no_reverse_api_or_ui_source_references():
    forbidden = ("src.api", "src.ui", "fastapi", "streamlit", "flowsync", "competitor")
    for path in FACADE_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8-sig").lower()
        assert all(value not in source for value in forbidden), path
