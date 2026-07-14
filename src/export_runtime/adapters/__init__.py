"""Deterministic no-I/O export adapter placeholders."""

from .placeholder import FailingPlaceholderAdapter, SuccessfulPlaceholderAdapter, UnavailablePlaceholderAdapter

__all__ = [
    "FailingPlaceholderAdapter",
    "SuccessfulPlaceholderAdapter",
    "UnavailablePlaceholderAdapter",
]
