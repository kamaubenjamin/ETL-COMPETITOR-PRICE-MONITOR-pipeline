"""Backward-compatible Review Runtime exception exports."""

from src.review_runtime.errors import ReviewRuntimeError


class ReviewItemNotFoundError(ReviewRuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__("review_item_not_found", message)


class InvalidReviewStateError(ReviewRuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__("invalid_review_state", message)
