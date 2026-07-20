"""Vercel ASGI entrypoint for the existing Document Intelligence API."""

from src.api.document_intelligence.app import app


__all__ = ["app"]
