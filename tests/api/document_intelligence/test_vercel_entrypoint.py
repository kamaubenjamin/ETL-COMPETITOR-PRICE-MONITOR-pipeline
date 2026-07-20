import json
import os
import subprocess
import sys
from pathlib import Path

from api.index import app as vercel_app
from src.api.document_intelligence.app import app as existing_app
from tests.api.document_intelligence.asgi_client import asgi_request


ROOT = Path(__file__).resolve().parents[3]


def test_vercel_entrypoint_reexports_the_existing_fastapi_instance() -> None:
    assert vercel_app is existing_app


def test_health_and_documentation_routes_work_through_vercel_entrypoint() -> None:
    for path in ("/health", "/api/v1/health", "/docs", "/redoc", "/openapi.json"):
        response = asgi_request(vercel_app, "GET", path)
        assert response.status_code == 200

    health = asgi_request(vercel_app, "GET", "/health").json()
    assert health["data"] == {
        "service": "document-intelligence-api",
        "status": "ok",
        "mode": "read_only_foundation",
    }
    assert "path" not in str(health).lower()
    assert "secret" not in str(health).lower()


def test_vercel_runtime_and_minimal_manifest_are_explicit() -> None:
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.12"
    manifest = (ROOT / "requirements-api.txt").read_text(encoding="utf-8").lower()
    dependencies = [line for line in manifest.splitlines() if line and not line.startswith("#")]

    assert dependencies == [
        "fastapi==0.139.2",
        "httpx==0.28.1",
        "pyjwt[crypto]==2.10.1",
    ]
    for prohibited in (
        "pandas",
        "numpy",
        "streamlit",
        "selenium",
        "playwright",
        "pytest",
        "reportlab",
        "rapidfuzz",
        "beautifulsoup",
        "lxml",
        "uvicorn",
    ):
        assert prohibited not in manifest

    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    assert config["installCommand"] == "python -m pip install -r requirements-api.txt"
    assert "api/index.py" in config["functions"]
    assert "rewrites" not in config


def test_api_runtime_dependency_validator_passes_for_the_active_interpreter() -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_api_runtime_dependencies.py")],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "api runtime dependency validation passed" in result.stdout.lower()


def test_vercel_entrypoint_does_not_eagerly_import_tabular_dependencies() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from api.index import app; import sys; "
                "assert 'pandas' not in sys.modules; "
                "assert 'numpy' not in sys.modules; "
                "paths=set(app.openapi()['paths']); "
                "assert '/health' in paths; "
                "assert '/api/v1/health' in paths; "
                "assert '/api/v1/workflow-definitions' in paths"
            ),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_public_transform_api_executes_when_explicitly_requested() -> None:
    import pandas as pd

    from src.transforms import aggregate_data

    result = aggregate_data(
        pd.DataFrame({"amount": [10, 20]}),
        {
            "contract_version": 1,
            "group_by": [],
            "aggregations": [{"field": "amount", "function": "sum", "output": "total"}],
            "drop_null_groups": False,
        },
    )

    assert result.to_dict("records") == [{"total": 30}]


def test_workflow_runtime_public_exports_resolve_when_explicitly_requested() -> None:
    import src.workflow_runtime as workflow_runtime
    from src.workflow_runtime.dsl.workflow_parser import WorkflowParser
    from src.workflow_runtime.locking import LockProvider

    assert "WorkflowParser" in dir(workflow_runtime)
    assert workflow_runtime.WorkflowParser is WorkflowParser
    assert workflow_runtime.LockProvider is LockProvider


def test_runtime_is_executing_a_supported_python_312_interpreter() -> None:
    assert sys.version_info[:2] == (3, 12)
