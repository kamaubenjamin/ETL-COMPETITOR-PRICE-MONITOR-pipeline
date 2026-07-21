"""Safe authenticated session projection for the FlowSync browser."""

from fastapi import APIRouter, Request

from ..auth import resolve_authenticated_principal
from ..responses import success_response


router = APIRouter(prefix="/api/v1/session", tags=["session"])


@router.get("")
def get_session(request: Request) -> dict[str, object]:
    principal = resolve_authenticated_principal(request)
    data: dict[str, object] = {
        "authenticated": True,
        "tenant_name": principal.metadata.get("tenant_name"),
        "tenant_slug": principal.metadata.get("tenant_slug"),
        "role": principal.metadata.get("membership_role"),
        "permissions": [permission.value for permission in principal.effective_permissions],
    }
    if principal.display_name:
        data["email"] = principal.display_name
    return success_response(data, request_id=request.state.request_id)
