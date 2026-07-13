"""Deterministic providers for the Document Intelligence API."""

from .local_provider import LocalDocumentIntelligenceProvider, local_provider

__all__ = ["LocalDocumentIntelligenceProvider", "local_provider"]
