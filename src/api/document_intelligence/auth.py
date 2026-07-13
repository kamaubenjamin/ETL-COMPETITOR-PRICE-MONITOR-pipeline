"""API-local identity resolution and read authorization composition."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from src.security import (
    AuthorizationContext,
    AuthorizationMode,
    AuthorizationRequest,
    DecisionReason,
    Permission,
    PermissionGuard,
)
from src.security.providers import IdentityProvider, IdentityProviderResult, LocalIdentityProvider

from .config import APIAuthConfig, APIAuthMode
from .errors import DocumentIntelligenceAPIError


@dataclass(frozen=True, slots=True)
class AuthorizedReadScope:
    enabled: bool
    tenant_id: str | None = None
    principal_id: str | None = None


@dataclass(frozen=True, slots=True)
class APIAuthComposition:
    config: APIAuthConfig
    identity_provider: IdentityProvider | None
    guard: PermissionGuard

    def __post_init__(self) -> None:
        if not isinstance(self.config, APIAuthConfig):
            raise ValueError("config must be APIAuthConfig")
        if not isinstance(self.guard, PermissionGuard):
            raise ValueError("guard must be PermissionGuard")
        if not self.config.enabled:
            if self.identity_provider is not None:
                raise ValueError("disabled auth cannot configure an identity provider")
            return
        if self.identity_provider is None or not isinstance(self.identity_provider, IdentityProvider):
            raise ValueError("enabled auth requires an identity provider")
        is_local = isinstance(self.identity_provider, LocalIdentityProvider)
        if self.config.mode == APIAuthMode.LOCAL_DEMO and not is_local:
            raise ValueError("local_demo mode requires the local identity provider")
        if self.config.mode != APIAuthMode.LOCAL_DEMO and is_local:
            raise ValueError("local identity provider is allowed only in local_demo mode")


def create_auth_composition(
    config: APIAuthConfig | None = None,
    identity_provider: IdentityProvider | None = None,
) -> APIAuthComposition:
    return APIAuthComposition(config or APIAuthConfig(), identity_provider, PermissionGuard())


def _composition(request: Request) -> APIAuthComposition:
    application = request.scope.get("app")
    configured = getattr(getattr(application, "state", None), "document_intelligence_auth", None)
    if configured is None:
        return create_auth_composition()
    if not isinstance(configured, APIAuthComposition):
        raise DocumentIntelligenceAPIError(
            "auth_configuration_error",
            "Authorization could not be evaluated.",
            status_code=500,
        )
    return configured


def _auth_error(*, status_code: int, concealed: bool = False) -> DocumentIntelligenceAPIError:
    if concealed:
        return DocumentIntelligenceAPIError("resource_not_found", "Resource was not found.", status_code=404)
    if status_code == 401:
        return DocumentIntelligenceAPIError("authentication_required", "Authentication is required.", status_code=401)
    return DocumentIntelligenceAPIError("authorization_denied", "Access is denied.", status_code=403)


def authorize_read(
    request: Request,
    permission: Permission,
    *,
    resource_type: str,
    resource_id: str | None = None,
    conceal_unauthorized_resource: bool = False,
) -> AuthorizedReadScope:
    composition = _composition(request)
    if not composition.config.enabled:
        return AuthorizedReadScope(False)

    identity_id = request.headers.get(composition.config.identity_header)
    try:
        result = composition.identity_provider.resolve(identity_id)
    except Exception:
        raise DocumentIntelligenceAPIError(
            "identity_provider_unavailable",
            "Identity could not be resolved.",
            status_code=503,
        ) from None
    if not isinstance(result, IdentityProviderResult):
        raise DocumentIntelligenceAPIError(
            "identity_provider_unavailable",
            "Identity could not be resolved.",
            status_code=503,
        )
    if not result.resolved or result.principal is None:
        raise _auth_error(status_code=401)
    principal = result.principal
    requested_tenant = request.headers.get(composition.config.tenant_header)
    if requested_tenant is None and principal.tenant_scope.tenant_ids:
        requested_tenant = principal.tenant_scope.tenant_ids[0]
    try:
        context = AuthorizationContext(
            principal=principal,
            active_tenant_id=requested_tenant,
            mode=(
                AuthorizationMode.LOCAL_PREVIEW
                if composition.config.mode == APIAuthMode.LOCAL_DEMO
                else AuthorizationMode.PRODUCTION
                if composition.config.mode == APIAuthMode.PRODUCTION
                else AuthorizationMode.AUTHENTICATED
            ),
            allow_cross_tenant=composition.config.allow_cross_tenant,
            request_id=getattr(request.state, "request_id", None),
        )
        authorization_request = AuthorizationRequest(
            required_permission=permission,
            requested_tenant_id=requested_tenant,
            resource_tenant_id=requested_tenant,
            resource_id=resource_id,
            resource_type=resource_type,
            operation="read",
        )
    except ValueError:
        raise DocumentIntelligenceAPIError(
            "invalid_request",
            "Authorization request is invalid.",
            status_code=400,
        ) from None
    decision = composition.guard(context, authorization_request)
    if not decision.allowed:
        unauthenticated = decision.reason in {
            DecisionReason.MISSING_IDENTITY,
            DecisionReason.UNAUTHENTICATED,
        }
        raise _auth_error(
            status_code=401 if unauthenticated else 403,
            concealed=conceal_unauthorized_resource and not unauthenticated,
        )
    return AuthorizedReadScope(True, requested_tenant, principal.principal_id)
