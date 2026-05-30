from __future__ import annotations

from typing import Dict, Optional

from src.review_runtime.contracts.repository import FeedbackRepository
from src.review_runtime.models.feedback_record import FeedbackRecord


class InMemoryFeedbackRepository(FeedbackRepository):
    def __init__(self) -> None:
        self._store: Dict[str, FeedbackRecord] = {}

    def save_feedback(self, review_id: str, feedback: FeedbackRecord) -> FeedbackRecord:
        self._store[review_id] = feedback
        return feedback

    def get_feedback(self, review_id: str) -> Optional[FeedbackRecord]:
        return self._store.get(review_id)
