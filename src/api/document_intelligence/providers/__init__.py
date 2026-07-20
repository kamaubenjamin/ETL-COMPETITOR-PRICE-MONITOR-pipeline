"""Read-only providers for the Document Intelligence API."""

from fastapi import Request

from ..errors import DocumentIntelligenceAPIError
from .facade_provider import FacadeDocumentIntelligenceProvider, facade_provider
from .local_provider import LocalDocumentIntelligenceProvider, local_provider as api_local_provider
from .workflow_studio_provider import WorkflowStudioAPIProvider

# Routers retain this compatibility name while the facade-backed source becomes preferred.
local_provider = facade_provider


def get_document_intelligence_provider(request: Request):
    """Resolve the app-scoped provider, retaining the local compatibility default."""

    application = request.scope.get("app")
    configured = getattr(
        getattr(application, "state", None),
        "document_intelligence_provider",
        None,
    )
    if configured is None:
        return local_provider
    if not isinstance(configured, FacadeDocumentIntelligenceProvider):
        raise DocumentIntelligenceAPIError(
            "provider_configuration_error",
            "Document data could not be read.",
            status_code=500,
        )
    return configured

__all__ = [
    "FacadeDocumentIntelligenceProvider",
    "LocalDocumentIntelligenceProvider",
    "WorkflowStudioAPIProvider",
    "api_local_provider",
    "facade_provider",
    "get_document_intelligence_provider",
    "local_provider",
]
