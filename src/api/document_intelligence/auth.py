"""API-local identity resolution and tenant authorization composition."""

from __future__ import annotations

from dataclasses import dataclass
from re import fullmatch

from fastapi import Request

from src.platform_runtime import AuthConfig as RuntimeAuthConfig
from src.security import (
    AuthorizationContext,
    AuthorizationMode,
    AuthorizationRequest,
    DecisionReason,
    Permission,
    PermissionGuard,
    Principal,
)
from src.security.providers import IdentityProvider, LocalIdentityProvider, create_local_demo_provider

from .config import APIAuthConfig, APIAuthMode, SupabaseAuthConfig, api_auth_config_from_runtime
from .errors import DocumentIntelligenceAPIError
from .supabase_auth import (
    SupabaseAuthenticationError,
    SupabaseAuthorizationError,
    SupabaseIdentityProvider,
    SupabaseJWTVerifier,
    SupabaseMembershipResolver,
    SupabaseProviderUnavailable,
)


@dataclass(frozen=True, slots=True)
class AuthorizedReadScope:
    enabled: bool
    tenant_id: str | None = None
    principal_id: str | None = None
    tenant_name: str | None = None
    tenant_slug: str | None = None


@dataclass(frozen=True, slots=True)
class APIAuthComposition:
    config: APIAuthConfig
    identity_provider: IdentityProvider | None
    guard: PermissionGuard

    def __post_init__(self) -> None:
        if not isinstance(self.config, APIAuthConfig) or not isinstance(self.guard, PermissionGuard):
            raise ValueError("authorization composition is invalid")
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
        if self.config.mode == APIAuthMode.SUPABASE and not isinstance(self.identity_provider, SupabaseIdentityProvider):
            raise ValueError("supabase mode requires the Supabase identity provider")


def create_auth_composition(
    config: APIAuthConfig | None = None,
    identity_provider: IdentityProvider | None = None,
) -> APIAuthComposition:
    return APIAuthComposition(config or APIAuthConfig(), identity_provider, PermissionGuard())


def create_supabase_auth_composition(config: SupabaseAuthConfig) -> APIAuthComposition:
    provider = SupabaseIdentityProvider(
        SupabaseJWTVerifier(config),
        SupabaseMembershipResolver(config),
    )
    return create_auth_composition(APIAuthConfig(APIAuthMode.SUPABASE), provider)


def create_runtime_auth_composition(config: RuntimeAuthConfig) -> APIAuthComposition:
    """Create API auth from validated local platform config without environment inference."""

    api_config = api_auth_config_from_runtime(config)
    provider = create_local_demo_provider("tenant-demo") if api_config.mode == APIAuthMode.LOCAL_DEMO else None
    return create_auth_composition(api_config, provider)


def _composition(request: Request) -> APIAuthComposition:
    application = request.scope.get("app")
    configured = getattr(getattr(application, "state", None), "document_intelligence_auth", None)
    if configured is None:
        return create_auth_composition()
    if not isinstance(configured, APIAuthComposition):
        raise DocumentIntelligenceAPIError(
            "auth_configuration_error", "Authorization could not be evaluated.", status_code=500
        )
    return configured


def _auth_error(*, status_code: int, concealed: bool = False) -> DocumentIntelligenceAPIError:
    if concealed:
        return DocumentIntelligenceAPIError("resource_not_found", "Resource was not found.", status_code=404)
    if status_code == 401:
        return DocumentIntelligenceAPIError(
            "authentication_required", "Authentication is required.", status_code=401
        )
    return DocumentIntelligenceAPIError("authorization_denied", "Access is denied.", status_code=403)


def _bearer_token(request: Request) -> str:
    value = request.headers.get("authorization")
    if not value or len(value) > 16400:
        raise _auth_error(status_code=401)
    parts = value.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        raise _auth_error(status_code=401)
    return parts[1]


def resolve_authenticated_principal(request: Request) -> Principal:
    composition = _composition(request)
    if not composition.config.enabled:
        raise _auth_error(status_code=401)
    if composition.config.mode == APIAuthMode.SUPABASE:
        if request.headers.get(composition.config.identity_header) or request.headers.get(composition.config.tenant_header):
            raise _auth_error(status_code=403)
        identity_value = _bearer_token(request)
    else:
        identity_value = request.headers.get(composition.config.identity_header)
    try:
        result = composition.identity_provider.resolve(identity_value)
    except SupabaseAuthenticationError:
        raise _auth_error(status_code=401) from None
    except SupabaseAuthorizationError:
        raise _auth_error(status_code=403) from None
    except SupabaseProviderUnavailable:
        raise DocumentIntelligenceAPIError(
            "identity_provider_unavailable", "Identity could not be resolved.", status_code=503
        ) from None
    except Exception:
        raise DocumentIntelligenceAPIError(
            "identity_provider_unavailable", "Identity could not be resolved.", status_code=503
        ) from None
    if not result.resolved or result.principal is None:
        raise _auth_error(status_code=401)
    return result.principal


def _authorized_scope(
    request: Request,
    permission: Permission,
    *,
    resource_type: str,
    resource_id: str | None,
    operation: str,
    conceal_unauthorized_resource: bool = False,
) -> AuthorizedReadScope:
    composition = _composition(request)
    if not composition.config.enabled:
        return AuthorizedReadScope(False)
    principal = resolve_authenticated_principal(request)
    if composition.config.mode == APIAuthMode.SUPABASE:
        requested_tenant = principal.tenant_scope.tenant_ids[0] if len(principal.tenant_scope.tenant_ids) == 1 else None
    else:
        requested_tenant = request.headers.get(composition.config.tenant_header)
        if requested_tenant is None and principal.tenant_scope.tenant_ids:
            requested_tenant = principal.tenant_scope.tenant_ids[0]
    if requested_tenant is None:
        raise _auth_error(status_code=403)
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
            operation=operation,
        )
    except ValueError:
        raise DocumentIntelligenceAPIError(
            "invalid_request", "Authorization request is invalid.", status_code=400
        ) from None
    decision = composition.guard(context, authorization_request)
    if not decision.allowed:
        unauthenticated = decision.reason in {DecisionReason.MISSING_IDENTITY, DecisionReason.UNAUTHENTICATED}
        raise _auth_error(
            status_code=401 if unauthenticated else 403,
            concealed=conceal_unauthorized_resource and not unauthenticated,
        )
    tenant_name = principal.metadata.get("tenant_name")
    if not isinstance(tenant_name, str) or not tenant_name or len(tenant_name) > 128:
        tenant_name = None
    tenant_slug = principal.metadata.get("tenant_slug")
    if (
        not isinstance(tenant_slug, str)
        or fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", tenant_slug) is None
    ):
        tenant_slug = None
    return AuthorizedReadScope(True, requested_tenant, principal.principal_id, tenant_name, tenant_slug)


def authorize_read(
    request: Request,
    permission: Permission,
    *,
    resource_type: str,
    resource_id: str | None = None,
    conceal_unauthorized_resource: bool = False,
) -> AuthorizedReadScope:
    return _authorized_scope(
        request,
        permission,
        resource_type=resource_type,
        resource_id=resource_id,
        operation="read",
        conceal_unauthorized_resource=conceal_unauthorized_resource,
    )


def authorize_mutation(
    request: Request,
    permission: Permission,
    *,
    resource_type: str,
    resource_id: str | None = None,
) -> AuthorizedReadScope:
    return _authorized_scope(
        request,
        permission,
        resource_type=resource_type,
        resource_id=resource_id,
        operation="write",
    )
