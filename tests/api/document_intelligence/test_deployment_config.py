import pytest

from src.api.document_intelligence.config import (
    APIDeploymentEnvironment,
    APIEnvironmentConfig,
)


def test_environment_config_defaults_are_local_and_cors_disabled() -> None:
    config = APIEnvironmentConfig.from_environment({})

    assert config.app_env == APIDeploymentEnvironment.LOCAL
    assert config.cors_allowed_origins == ()
    assert config.to_safe_dict() == {
        "app_env": "local",
        "cors_configured": False,
        "cors_origin_count": 0,
    }


def test_environment_config_normalizes_uat_and_origins_deterministically() -> None:
    config = APIEnvironmentConfig.from_environment(
        {
            "APP_ENV": " Technical_Preview ",
            "DOCUMENT_INTELLIGENCE_CORS_ALLOWED_ORIGINS": (
                "https://flowsync-uat.vercel.app/, http://127.0.0.1:4174,"
                "https://flowsync-uat.vercel.app"
            ),
        }
    )

    assert config.app_env == APIDeploymentEnvironment.UAT
    assert config.cors_allowed_origins == (
        "https://flowsync-uat.vercel.app",
        "http://127.0.0.1:4174",
    )
    assert config.to_safe_dict() == {
        "app_env": "uat",
        "cors_configured": True,
        "cors_origin_count": 2,
    }


@pytest.mark.parametrize(
    "value",
    ["*", "ftp://example.test", "https://user@example.test", "https://example.test/path", "not-an-origin"],
)
def test_environment_config_rejects_unsafe_cors_origins(value: str) -> None:
    with pytest.raises(ValueError, match="CORS allowed origins are invalid"):
        APIEnvironmentConfig(cors_allowed_origins=value)


def test_environment_reader_ignores_browser_and_reserved_secret_values() -> None:
    config = APIEnvironmentConfig.from_environment(
        {
            "APP_ENV": "uat",
            "VITE_SUPABASE_URL": "browser-value-is-not-server-config",
            "SUPABASE_SECRET_KEY": "not-consumed-in-phase-2",
            "DATABASE_URL": "not-consumed-in-phase-2",
            "JWT_ISSUER": "not-consumed-in-phase-2",
        }
    )

    assert config.to_safe_dict() == {
        "app_env": "uat",
        "cors_configured": False,
        "cors_origin_count": 0,
    }
