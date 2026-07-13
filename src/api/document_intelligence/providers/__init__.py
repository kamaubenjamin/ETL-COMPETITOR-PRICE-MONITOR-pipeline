"""Read-only providers for the Document Intelligence API."""

from .facade_provider import FacadeDocumentIntelligenceProvider, facade_provider
from .local_provider import LocalDocumentIntelligenceProvider, local_provider as api_local_provider

# Routers retain this compatibility name while the facade-backed source becomes preferred.
local_provider = facade_provider

__all__ = [
    "FacadeDocumentIntelligenceProvider",
    "LocalDocumentIntelligenceProvider",
    "api_local_provider",
    "facade_provider",
    "local_provider",
]
