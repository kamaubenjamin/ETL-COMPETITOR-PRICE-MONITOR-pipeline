import ast
from pathlib import Path


ROOT = Path("src/upload_runtime")
FORBIDDEN = {"api", "platform_runtime", "security", "export_runtime", "persistence", "sqlite3", "streamlit"}


def test_phase4_runtime_has_no_forbidden_imports():
    for path in ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = {node.module.split(".")[0]}
            else:
                continue
            assert not names.intersection(FORBIDDEN), (path, names)


def test_phase4_runtime_contains_no_io_or_processing_activation_calls():
    source = "\n".join(path.read_text(encoding="utf-8").lower() for path in ROOT.glob("*.py"))
    for forbidden in ("open(", "requests.", "subprocess", "export_runtime", "start_ingestion("):
        assert forbidden not in source

