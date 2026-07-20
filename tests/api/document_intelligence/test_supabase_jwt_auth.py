from datetime import datetime, timedelta, timezone

import httpx
import jwt
import pytest

from src.api.document_intelligence.supabase_auth import (
    SupabaseAuthenticationError,
    SupabaseJWTVerifier,
    SupabaseProviderUnavailable,
)
from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.config import APIEnvironmentConfig
from src.platform_runtime import RuntimeValidationError
from tests.api.document_intelligence.supabase_auth_helpers import (
    KID,
    OTHER_PRIVATE_KEY,
    PRIVATE_KEY,
    PUBLIC_JWK,
    USER_ID,
    config,
    token,
)


def verifier(*, status=200, keys=None, captured=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if captured is not None:
            captured.append(request)
        return httpx.Response(status, json={"keys": keys if keys is not None else [PUBLIC_JWK]})
    return SupabaseJWTVerifier(config(), http_client=httpx.Client(transport=httpx.MockTransport(handler), timeout=1))


@pytest.mark.parametrize("value", ["", "not-a-jwt", "a.b.c"])
def test_malformed_tokens_fail_closed(value):
    with pytest.raises(SupabaseAuthenticationError):
        verifier().verify(value)


def test_unsigned_and_unsupported_algorithms_fail_closed():
    claims = {"iss": config().issuer, "aud": "authenticated", "sub": USER_ID, "exp": 4102444800}
    unsigned = jwt.encode(claims, key="", algorithm="none", headers={"kid": KID})
    unsupported = jwt.encode(claims, key="fixture", algorithm="HS256", headers={"kid": KID})
    for value in (unsigned, unsupported):
        with pytest.raises(SupabaseAuthenticationError):
            verifier().verify(value)


@pytest.mark.parametrize("overrides", [
    {"exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
    {"iss": "https://wrong.example/auth/v1"},
    {"aud": "wrong"},
    {"sub": "not-a-uuid"},
    {"sub": None},
    {"nbf": datetime.now(timezone.utc) + timedelta(minutes=5)},
])
def test_invalid_registered_claims_fail_closed(overrides):
    with pytest.raises(SupabaseAuthenticationError):
        verifier().verify(token(**overrides))


def test_invalid_signature_fails_closed():
    now = datetime.now(timezone.utc)
    value = jwt.encode(
        {"iss": config().issuer, "aud": "authenticated", "sub": USER_ID, "exp": now + timedelta(minutes=5)},
        OTHER_PRIVATE_KEY,
        algorithm="RS256",
        headers={"kid": KID},
    )
    with pytest.raises(SupabaseAuthenticationError):
        verifier().verify(value)


def test_valid_jwt_is_verified_locally_and_cache_is_bounded():
    captured = []
    instance = verifier(captured=captured)
    assert instance.verify(token()).user_id == USER_ID
    assert instance.verify(token()).user_id == USER_ID
    assert len(captured) == 1
    assert instance.cached_key_count <= config().jwks_max_keys
    assert captured[0].extensions["timeout"]["connect"] == config().network_timeout_seconds


def test_jwks_failure_maps_to_safe_provider_unavailable_without_token_details():
    sensitive = token()
    with pytest.raises(SupabaseProviderUnavailable) as captured:
        verifier(status=503).verify(sensitive)
    assert sensitive not in str(captured.value)


def test_hosted_startup_fails_closed_without_supabase_configuration(monkeypatch):
    for name in ("SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY", "SUPABASE_JWKS_URL", "SUPABASE_JWT_ISSUER"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RuntimeValidationError):
        create_document_intelligence_app(environment_config=APIEnvironmentConfig(app_env="uat"))
