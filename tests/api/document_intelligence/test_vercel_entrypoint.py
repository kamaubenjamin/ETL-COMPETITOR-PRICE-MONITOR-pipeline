import json
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

    assert dependencies == ["fastapi==0.139.2", "httpx==0.28.1", "pyjwt[crypto]==2.10.1"]
    for prohibited in (
        "streamlit",
        "selenium",
        "playwright",
        "pytest",
        "pandas",
        "numpy",
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


def test_runtime_is_executing_a_supported_python_312_interpreter() -> None:
    assert sys.version_info[:2] == (3, 12)
