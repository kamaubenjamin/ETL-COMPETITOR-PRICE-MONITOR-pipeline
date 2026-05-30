from __future__ import annotations

from typing import Any, Dict, Optional

from src.contracts.api import utc_now_iso
from src.review_runtime.contracts.repository import FeedbackRepository
from src.review_runtime.models.feedback_record import FeedbackRecord
from src.review_runtime.models.review_correction import ReviewCorrection
from src.review_runtime.models.review_decision import ReviewDecision
from src.review_runtime.models.review_item import ReviewItem


class FeedbackService:
    def __init__(self, feedback_repository: FeedbackRepository) -> None:
        self.feedback_repository = feedback_repository

    def capture_feedback(
        self,
        review_item: ReviewItem,
        comment: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FeedbackRecord:
        feedback = self.build_feedback_record(
            review_item=review_item,
            decision=review_item.decision,
            correction=review_item.corrections[-1] if review_item.corrections else None,
            metadata=metadata or {},
        )
        return self.feedback_repository.save_feedback(review_item.review_id, feedback)

    def capture_correction(
        self,
        review_item: ReviewItem,
        corrected_value: str,
        reason: str,
        reviewer: str,
        comment: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FeedbackRecord:
        correction = ReviewCorrection(
            original_value=review_item.entity_value,
            corrected_value=corrected_value,
            reason=reason,
            reviewer=reviewer,
            timestamp=utc_now_iso(),
        )
        feedback = self.build_feedback_record(
            review_item=review_item,
            decision=ReviewDecision(
                decision="corrected",
                reviewer=reviewer,
                timestamp=utc_now_iso(),
                comment=comment,
            ),
            correction=correction,
            metadata=metadata or {},
        )
        return self.feedback_repository.save_feedback(review_item.review_id, feedback)

    def build_feedback_record(
        self,
        review_item: ReviewItem,
        decision: Optional[ReviewDecision] = None,
        correction: Optional[ReviewCorrection] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FeedbackRecord:
        return FeedbackRecord(
            review_id=review_item.review_id,
            outcome=review_item.status.value,
            review_item=review_item.to_dict(),
            decision=decision,
            correction=correction,
            created_at=utc_now_iso(),
            metadata=metadata or {},
        )
