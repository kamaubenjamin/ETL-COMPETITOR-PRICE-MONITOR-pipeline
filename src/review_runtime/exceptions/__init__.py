"""Review Runtime exceptions package."""

from __future__ import annotations


class ReviewRuntimeError(Exception):
    pass


class ReviewItemNotFoundError(ReviewRuntimeError):
    pass


class InvalidReviewStateError(ReviewRuntimeError):
    pass
