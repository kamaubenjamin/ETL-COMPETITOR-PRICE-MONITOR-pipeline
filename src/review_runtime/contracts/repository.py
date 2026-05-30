from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.review_runtime.models.review_item import ReviewItem
from src.review_runtime.models.feedback_record import FeedbackRecord


class ReviewRepository(ABC):
    @abstractmethod
    def create_review_item(self, review_item: ReviewItem) -> ReviewItem:
        ...

    @abstractmethod
    def get_review_item(self, review_id: str) -> Optional[ReviewItem]:
        ...

    @abstractmethod
    def update_review_item(self, review_item: ReviewItem) -> ReviewItem:
        ...

    @abstractmethod
    def list_pending_reviews(self) -> List[ReviewItem]:
        ...


class FeedbackRepository(ABC):
    @abstractmethod
    def save_feedback(self, review_id: str, feedback: FeedbackRecord) -> FeedbackRecord:
        ...

    @abstractmethod
    def get_feedback(self, review_id: str) -> Optional[FeedbackRecord]:
        ...
