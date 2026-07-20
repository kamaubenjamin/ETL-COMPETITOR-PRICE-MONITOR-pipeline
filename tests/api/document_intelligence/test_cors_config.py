import pytest

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.config import APIAuthConfig, APIAuthMode, APIEnvironmentConfig
from tests.api.document_intelligence.asgi_client import asgi_request
from tests.api.document_intelligence.supabase_auth_helpers import provider


ALLOWED_ORIGIN = "https://future-frontend-project.vercel.app"


def _application(origins: str = ""):
    return create_document_intelligence_app(
        auth_config=APIAuthConfig(APIAuthMode.SUPABASE),
        identity_provider=provider(),
        environment_config=APIEnvironmentConfig(
            app_env="uat",
            cors_allowed_origins=origins,
        )
    )


def _preflight(application, origin: str, method: str = "GET", headers: str | None = None):
    request_headers = {
        "Origin": origin,
        "Access-Control-Request-Method": method,
    }
    if headers is not None:
        request_headers["Access-Control-Request-Headers"] = headers
    return asgi_request(application, "OPTIONS", "/api/v1/health", headers=request_headers)


def test_cors_is_disabled_when_no_origin_is_configured() -> None:
    response = _preflight(_application(), ALLOWED_ORIGIN)

    assert response.status_code == 405
    assert "access-control-allow-origin" not in response.headers


def test_exact_configured_origin_is_allowed_without_credentials() -> None:
    response = _preflight(_application(ALLOWED_ORIGIN), ALLOWED_ORIGIN, headers="content-type,x-request-id")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "access-control-allow-credentials" not in response.headers
    assert response.headers["access-control-max-age"] == "600"


def test_unconfigured_origin_and_unneeded_methods_are_denied_but_authorization_is_allowed() -> None:
    application = _application(ALLOWED_ORIGIN)

    assert _preflight(application, "https://other.example.test").status_code == 400
    assert _preflight(application, ALLOWED_ORIGIN, method="DELETE").status_code == 400
    assert _preflight(application, ALLOWED_ORIGIN, headers="authorization").status_code == 200


@pytest.mark.parametrize(
    "origin",
    (
        "*",
        "https://user:password@example.test",
        "https://example.test/path",
        "https://example.test?query=value",
        "https://example.test#fragment",
    ),
)
def test_unsafe_origins_are_rejected(origin: str) -> None:
    with pytest.raises(ValueError, match="CORS allowed origins are invalid"):
        APIEnvironmentConfig(app_env="uat", cors_allowed_origins=origin)


def test_uat_configuration_is_deterministic_and_exposes_only_safe_metadata() -> None:
    config = APIEnvironmentConfig.from_environment(
        {
            "APP_ENV": "uat",
            "DOCUMENT_INTELLIGENCE_CORS_ALLOWED_ORIGINS": ALLOWED_ORIGIN,
            "SUPABASE_SECRET_KEY": "must-not-be-read",
            "DATABASE_URL": "must-not-be-read",
        }
    )

    assert config.cors_allowed_origins == (ALLOWED_ORIGIN,)
    assert config.to_safe_dict() == {
        "app_env": "uat",
        "cors_configured": True,
        "cors_origin_count": 1,
    }
    assert "secret" not in str(config.to_safe_dict()).lower()
    assert "database" not in str(config.to_safe_dict()).lower()
