"""Supabase JWT verification and RLS-constrained tenant membership resolution."""

from __future__ import annotations

from dataclasses import dataclass
from re import fullmatch
from threading import RLock
from time import monotonic
from types import MappingProxyType
from typing import Any
from uuid import UUID

import httpx
import jwt
from jwt import PyJWK

from src.security import Permission, Principal, PrincipalType, TenantScope
from src.security.providers import (
    IdentityProviderResult,
    IdentityResolutionReason,
    IdentityResolutionStatus,
)

from .config import SupabaseAuthConfig


SUPPORTED_JWT_ALGORITHMS = frozenset({"RS256", "ES256"})
UAT_ROLE_PERMISSIONS = MappingProxyType(
    {
        "owner": frozenset(
            {
                Permission.DOCUMENT_READ,
                Permission.DOCUMENT_LIST,
                Permission.WORKFLOW_READ,
                Permission.WORKFLOW_CREATE,
                Permission.WORKFLOW_EDIT,
                Permission.WORKFLOW_TEST,
                Permission.WORKFLOW_APPROVE,
                Permission.WORKFLOW_PUBLISH,
                Permission.WORKFLOW_DEACTIVATE,
                Permission.WORKFLOW_ADMIN,
            }
        ),
        "reviewer": frozenset(
            {
                Permission.DOCUMENT_READ,
                Permission.DOCUMENT_LIST,
                Permission.WORKFLOW_READ,
                Permission.WORKFLOW_TEST,
            }
        ),
        "viewer": frozenset(
            {
                Permission.DOCUMENT_READ,
                Permission.DOCUMENT_LIST,
                Permission.WORKFLOW_READ,
            }
        ),
    }
)


class SupabaseAuthenticationError(Exception):
    """The bearer credential is missing, malformed, or cryptographically invalid."""


class SupabaseAuthorizationError(Exception):
    """The verified user has no unambiguous active tenant authority."""


class SupabaseProviderUnavailable(Exception):
    """The external verification or membership boundary is temporarily unavailable."""


@dataclass(frozen=True, slots=True)
class VerifiedSupabaseIdentity:
    user_id: str
    email: str | None = None


@dataclass(frozen=True, slots=True)
class TenantMembership:
    tenant_id: str
    tenant_name: str
    tenant_slug: str
    role: str


class SupabaseJWTVerifier:
    """Verify asymmetric Supabase access tokens with a bounded in-memory JWKS cache."""

    def __init__(self, config: SupabaseAuthConfig, *, http_client: httpx.Client | None = None) -> None:
        self._config = config
        self._client = http_client or httpx.Client(
            timeout=httpx.Timeout(config.network_timeout_seconds),
            verify=True,
        )
        self._keys: dict[str, tuple[str, Any]] = {}
        self._expires_at = 0.0
        self._lock = RLock()

    @property
    def cached_key_count(self) -> int:
        with self._lock:
            return len(self._keys)

    def _refresh_keys(self) -> None:
        try:
            response = self._client.get(self._config.jwks_url, headers={"Accept": "application/json"})
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError, TypeError):
            raise SupabaseProviderUnavailable() from None
        keys = payload.get("keys") if isinstance(payload, dict) else None
        if not isinstance(keys, list) or not keys or len(keys) > 64:
            raise SupabaseProviderUnavailable()
        resolved: dict[str, tuple[str, Any]] = {}
        for item in keys:
            if not isinstance(item, dict):
                continue
            kid, algorithm = item.get("kid"), item.get("alg")
            if (
                not isinstance(kid, str)
                or not kid
                or len(kid) > 128
                or algorithm not in SUPPORTED_JWT_ALGORITHMS
                or kid in resolved
            ):
                continue
            try:
                resolved[kid] = (algorithm, PyJWK.from_dict(item, algorithm=algorithm).key)
            except (jwt.PyJWTError, ValueError, TypeError):
                continue
            if len(resolved) >= self._config.jwks_max_keys:
                break
        if not resolved:
            raise SupabaseProviderUnavailable()
        self._keys = resolved
        self._expires_at = monotonic() + self._config.jwks_cache_seconds

    def _key(self, kid: str, algorithm: str) -> Any:
        with self._lock:
            if monotonic() >= self._expires_at or kid not in self._keys:
                self._refresh_keys()
            resolved = self._keys.get(kid)
            if resolved is None or resolved[0] != algorithm:
                raise SupabaseAuthenticationError()
            return resolved[1]

    def verify(self, token: str) -> VerifiedSupabaseIdentity:
        if not isinstance(token, str) or not token or len(token) > 16384:
            raise SupabaseAuthenticationError()
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError:
            raise SupabaseAuthenticationError() from None
        algorithm, kid = header.get("alg"), header.get("kid")
        if algorithm not in SUPPORTED_JWT_ALGORITHMS or not isinstance(kid, str) or not kid or len(kid) > 128:
            raise SupabaseAuthenticationError()
        try:
            claims = jwt.decode(
                token,
                self._key(kid, algorithm),
                algorithms=[algorithm],
                issuer=self._config.issuer,
                audience=self._config.audience,
                options={"require": ["exp", "iss", "sub", "aud"]},
            )
            user_id = str(UUID(claims["sub"]))
        except SupabaseProviderUnavailable:
            raise
        except (jwt.PyJWTError, KeyError, TypeError, ValueError):
            raise SupabaseAuthenticationError() from None
        email = claims.get("email")
        if not isinstance(email, str) or not email or len(email) > 254 or any(ord(char) < 32 for char in email):
            email = None
        return VerifiedSupabaseIdentity(user_id=user_id, email=email)


class SupabaseMembershipResolver:
    """Read the verified user's own memberships through Data API RLS."""

    def __init__(self, config: SupabaseAuthConfig, *, http_client: httpx.Client | None = None) -> None:
        self._config = config
        self._client = http_client or httpx.Client(
            timeout=httpx.Timeout(config.network_timeout_seconds),
            verify=True,
        )

    def resolve(self, access_token: str, verified_user_id: str) -> TenantMembership:
        try:
            response = self._client.get(
                f"{self._config.url}/rest/v1/app_tenant_memberships",
                params={
                    "select": "tenant_id,role,status,app_tenants!inner(name,slug,status)",
                    "status": "eq.active",
                    "limit": "2",
                },
                headers={
                    "Accept": "application/json",
                    "apikey": self._config.publishable_key,
                    "Authorization": f"Bearer {access_token}",
                },
            )
        except httpx.HTTPError:
            raise SupabaseProviderUnavailable() from None
        if response.status_code in {401, 403}:
            raise SupabaseAuthorizationError()
        if response.status_code >= 400:
            raise SupabaseProviderUnavailable()
        try:
            rows = response.json()
        except ValueError:
            raise SupabaseProviderUnavailable() from None
        if not isinstance(rows, list) or len(rows) != 1:
            raise SupabaseAuthorizationError()
        row = rows[0]
        tenant = row.get("app_tenants") if isinstance(row, dict) else None
        if not isinstance(tenant, dict):
            raise SupabaseAuthorizationError()
        tenant_id, tenant_name, tenant_slug, tenant_status, role, membership_status = (
            row.get("tenant_id"),
            tenant.get("name"),
            tenant.get("slug"),
            tenant.get("status"),
            row.get("role"),
            row.get("status"),
        )
        try:
            tenant_id = str(UUID(tenant_id))
        except (TypeError, ValueError):
            raise SupabaseAuthorizationError() from None
        if (
            membership_status != "active"
            or tenant_status != "active"
            or role not in UAT_ROLE_PERMISSIONS
            or not isinstance(tenant_name, str)
            or not tenant_name
            or len(tenant_name) > 128
            or any(ord(char) < 32 for char in tenant_name)
            or not isinstance(tenant_slug, str)
            or fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", tenant_slug) is None
        ):
            raise SupabaseAuthorizationError()
        if str(UUID(verified_user_id)) != verified_user_id:
            raise SupabaseAuthorizationError()
        return TenantMembership(
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            tenant_slug=tenant_slug,
            role=role,
        )


class SupabaseIdentityProvider:
    """Map a verified subject and authoritative membership into core security contracts."""

    def __init__(self, verifier: SupabaseJWTVerifier, memberships: SupabaseMembershipResolver) -> None:
        self._verifier = verifier
        self._memberships = memberships

    def resolve(self, access_token: str | None) -> IdentityProviderResult:
        if access_token is None:
            raise SupabaseAuthenticationError()
        identity = self._verifier.verify(access_token)
        membership = self._memberships.resolve(access_token, identity.user_id)
        principal = Principal(
            principal_id=identity.user_id,
            principal_type=PrincipalType.USER,
            is_authenticated=True,
            tenant_scope=TenantScope((membership.tenant_id,)),
            explicit_permissions=tuple(UAT_ROLE_PERMISSIONS[membership.role]),
            display_name=identity.email,
            authentication_method="supabase_jwt",
            metadata={
                "membership_role": membership.role,
                "tenant_name": membership.tenant_name,
                "tenant_slug": membership.tenant_slug,
            },
        )
        return IdentityProviderResult(
            IdentityResolutionStatus.RESOLVED,
            IdentityResolutionReason.IDENTITY_RESOLVED,
            principal,
        )
