from __future__ import annotations

from typing import Dict, List, Optional

from src.review_runtime.contracts.repository import ReviewRepository
from src.review_runtime.models.review_item import ReviewItem
from src.review_runtime.models.status import ReviewStatus
from src.review_runtime.exceptions import ReviewItemNotFoundError


class InMemoryReviewRepository(ReviewRepository):
    def __init__(self) -> None:
        self._store: Dict[str, ReviewItem] = {}

    def create_review_item(self, review_item: ReviewItem) -> ReviewItem:
        self._store[review_item.review_id] = review_item
        return review_item

    def get_review_item(self, review_id: str) -> Optional[ReviewItem]:
        return self._store.get(review_id)

    def update_review_item(self, review_item: ReviewItem) -> ReviewItem:
        if review_item.review_id not in self._store:
            raise ReviewItemNotFoundError(f"Review item {review_item.review_id} not found")
        self._store[review_item.review_id] = review_item
        return review_item

    def list_pending_reviews(self) -> List[ReviewItem]:
        return [
            item for item in self._store.values() if item.status == ReviewStatus.PENDING
        ]
