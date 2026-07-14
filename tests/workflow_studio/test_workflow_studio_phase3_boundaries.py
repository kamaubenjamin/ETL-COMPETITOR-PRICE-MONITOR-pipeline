import ast
from pathlib import Path


PACKAGE = Path("src/workflow_studio")
PHASE3 = {
    "repositories.py", "store.py", "versioning.py", "draft_lifecycle.py",
    "publication.py", "audit.py", "repository_errors.py", "policy_errors.py",
}
FORBIDDEN = {
    "api", "apps", "document_state", "export_runtime", "platform_runtime", "security",
    "storage", "streamlit", "telemetry", "upload_runtime", "workflow_runtime", "sqlite3",
    "requests", "httpx", "openai",
}


def test_phase3_imports_are_standard_library_or_package_local_only() -> None:
    for filename in PHASE3:
        tree = ast.parse((PACKAGE / filename).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and not node.level:
                assert (node.module or "").split(".")[0] not in FORBIDDEN | {"src"}
            if isinstance(node, ast.Import):
                assert not {item.name.split(".")[0] for item in node.names}.intersection(FORBIDDEN)


def test_phase3_has_no_execution_database_file_or_network_calls() -> None:
    forbidden = {"eval", "exec", "open", "__import__", "connect", "urlopen"}
    for filename in PHASE3:
        tree = ast.parse((PACKAGE / filename).read_text(encoding="utf-8"))
        calls = {
            node.func.id if isinstance(node.func, ast.Name) else node.func.attr
            for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute))
        }
        assert not calls.intersection(forbidden)


def test_existing_source_packages_still_do_not_import_workflow_studio() -> None:
    matches = []
    for path in Path("src").glob("*/**/*.py"):
        if PACKAGE in path.parents:
            continue
        if "workflow_studio" in path.read_text(encoding="utf-8-sig"):
            matches.append(str(path))
    assert matches == []
