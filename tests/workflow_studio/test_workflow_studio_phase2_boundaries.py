import ast
from pathlib import Path


PACKAGE = Path("src/workflow_studio")
PHASE2 = {
    "validation.py", "dependencies.py", "compatibility.py", "legacy.py",
    "validation_results.py", "validation_errors.py", "path_validation.py",
}
FORBIDDEN = {
    "api", "apps", "document_state", "export_runtime", "platform_runtime", "security",
    "storage", "streamlit", "telemetry", "upload_runtime", "workflow_runtime", "sqlite3",
    "requests", "httpx", "openai",
}


def test_phase2_modules_import_only_standard_library_and_package_local_modules() -> None:
    for path in PACKAGE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.level:
                    continue
                assert (node.module or "").split(".")[0] not in FORBIDDEN
                assert (node.module or "").split(".")[0] != "src"
            if isinstance(node, ast.Import):
                assert not {alias.name.split(".")[0] for alias in node.names}.intersection(FORBIDDEN)


def test_phase2_modules_have_no_execution_or_io_calls() -> None:
    forbidden = {"eval", "exec", "open", "__import__"}
    for filename in PHASE2:
        tree = ast.parse((PACKAGE / filename).read_text(encoding="utf-8"))
        calls = {
            node.func.id if isinstance(node.func, ast.Name) else node.func.attr
            for node in ast.walk(tree) if isinstance(node, ast.Call)
            and isinstance(node.func, (ast.Name, ast.Attribute))
        }
        assert not calls.intersection(forbidden)


def test_existing_source_packages_do_not_import_workflow_studio() -> None:
    matches = []
    for path in Path("src").glob("*/**/*.py"):
        if PACKAGE in path.parents:
            continue
        text = path.read_text(encoding="utf-8-sig")
        if "workflow_studio" in text:
            matches.append(str(path))
    assert matches == [
        str(path) for path in Path("src/api/document_intelligence").rglob("*.py")
        if "workflow_studio" in path.read_text(encoding="utf-8-sig")
    ]
