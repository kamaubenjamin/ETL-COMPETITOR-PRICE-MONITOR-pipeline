from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from src.api.document_intelligence.app import create_document_intelligence_app
from src.api.document_intelligence.config import APIAuthConfig, APIAuthMode, APIEnvironmentConfig, SupabaseAuthConfig
from src.api.document_intelligence.supabase_auth import (
    SupabaseIdentityProvider,
    SupabaseJWTVerifier,
    SupabaseMembershipResolver,
)


USER_ID = "11111111-1111-4111-8111-111111111111"
TENANT_ID = "22222222-2222-4222-8222-222222222222"
KID = "uat-test-key"
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_JWK = json.loads(RSAAlgorithm.to_jwk(PRIVATE_KEY.public_key())) | {"kid": KID, "alg": "RS256", "use": "sig"}


def config() -> SupabaseAuthConfig:
    return SupabaseAuthConfig(
        url="https://project-ref.supabase.co",
        publishable_key="sb_publishable_test_fixture",
        network_timeout_seconds=1,
        jwks_cache_seconds=60,
        jwks_max_keys=2,
    )


def token(**overrides) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "iss": "https://project-ref.supabase.co/auth/v1",
        "aud": "authenticated",
        "sub": USER_ID,
        "exp": now + timedelta(minutes=10),
        "iat": now,
        "email": "uat-owner@example.test",
    }
    claims.update(overrides)
    return jwt.encode(claims, PRIVATE_KEY, algorithm="RS256", headers={"kid": KID})


def membership(
    role="owner",
    *,
    status="active",
    tenant_status="active",
    tenant_name="FlowSync UAT",
    tenant_slug="flowsync-uat",
):
    return [{
        "tenant_id": TENANT_ID,
        "role": role,
        "status": status,
        "app_tenants": {"name": tenant_name, "slug": tenant_slug, "status": tenant_status},
    }]


def provider(*, rows=None, jwks_status=200, capture=None) -> SupabaseIdentityProvider:
    cfg = config()
    membership_rows = membership() if rows is None else rows

    def handler(request: httpx.Request) -> httpx.Response:
        if capture is not None:
            capture.append(request)
        if request.url.path.endswith("/.well-known/jwks.json"):
            return httpx.Response(jwks_status, json={"keys": [PUBLIC_JWK]} if jwks_status == 200 else {})
        if request.url.path.endswith("/app_tenant_memberships"):
            return httpx.Response(200, json=membership_rows)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    verifier_client = httpx.Client(transport=transport, timeout=cfg.network_timeout_seconds)
    membership_client = httpx.Client(transport=transport, timeout=cfg.network_timeout_seconds)
    return SupabaseIdentityProvider(
        SupabaseJWTVerifier(cfg, http_client=verifier_client),
        SupabaseMembershipResolver(cfg, http_client=membership_client),
    )


def application(*, rows=None, jwks_status=200, capture=None):
    return create_document_intelligence_app(
        auth_config=APIAuthConfig(APIAuthMode.SUPABASE),
        identity_provider=provider(rows=rows, jwks_status=jwks_status, capture=capture),
        environment_config=APIEnvironmentConfig(app_env="uat"),
    )
