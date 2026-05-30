from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Optional

from src.contracts.api import utc_now_iso
from src.review_runtime.contracts.repository import FeedbackRepository, ReviewRepository
from src.review_runtime.exceptions import InvalidReviewStateError, ReviewItemNotFoundError
from src.review_runtime.models.feedback_record import FeedbackRecord
from src.review_runtime.models.review_correction import ReviewCorrection
from src.review_runtime.models.review_decision import ReviewDecision
from src.review_runtime.models.review_item import ReviewItem
from src.review_runtime.contracts.review_request import ReviewRequest
from src.review_runtime.models.status import ReviewStatus


class ReviewService:
    def __init__(
        self,
        review_repository: ReviewRepository,
        feedback_repository: FeedbackRepository,
        review_threshold: float = 0.7,
        auto_approve_threshold: float = 0.95,
    ) -> None:
        self.review_repository = review_repository
        self.feedback_repository = feedback_repository
        self.review_threshold = review_threshold
        self.auto_approve_threshold = auto_approve_threshold

    def create_review(self, request: ReviewRequest) -> ReviewItem:
        now = utc_now_iso()
        status = ReviewStatus.PENDING
        routing = "required_review"

        if request.confidence >= self.auto_approve_threshold:
            status = ReviewStatus.APPROVED
            routing = "auto_approved"
        elif request.confidence >= self.review_threshold:
            routing = "optional_review"

        item = ReviewItem(
            document_id=request.document_id,
            entity_type=request.entity_type,
            entity_value=request.entity_value,
            confidence=request.confidence,
            status=status,
            created_at=now,
            updated_at=now,
            metadata={**request.metadata, "routing": routing},
        )
        return self.review_repository.create_review_item(item)

    def get_review_item(self, review_id: str) -> ReviewItem:
        item = self.review_repository.get_review_item(review_id)
        if not item:
            raise ReviewItemNotFoundError(f"Review item {review_id} not found")
        return item

    def assign_review(self, review_id: str, reviewer: str) -> ReviewItem:
        item = self.get_review_item(review_id)
        if item.status != ReviewStatus.PENDING:
            raise InvalidReviewStateError("Only pending reviews can be assigned")
        updated = replace(item, status=ReviewStatus.IN_REVIEW, updated_at=utc_now_iso())
        return self.review_repository.update_review_item(updated)

    def approve_review(self, review_id: str, reviewer: str, comment: str = "") -> ReviewItem:
        item = self.get_review_item(review_id)
        if item.status not in {ReviewStatus.PENDING, ReviewStatus.IN_REVIEW}:
            raise InvalidReviewStateError("Review can only be approved from pending or in_review")
        decision = ReviewDecision(decision="approved", reviewer=reviewer, timestamp=utc_now_iso(), comment=comment)
        updated = replace(
            item,
            status=ReviewStatus.APPROVED,
            decision=decision,
            updated_at=utc_now_iso(),
        )
        return self.review_repository.update_review_item(updated)

    def reject_review(self, review_id: str, reviewer: str, comment: str = "") -> ReviewItem:
        item = self.get_review_item(review_id)
        if item.status not in {ReviewStatus.PENDING, ReviewStatus.IN_REVIEW}:
            raise InvalidReviewStateError("Review can only be rejected from pending or in_review")
        decision = ReviewDecision(decision="rejected", reviewer=reviewer, timestamp=utc_now_iso(), comment=comment)
        updated = replace(
            item,
            status=ReviewStatus.REJECTED,
            decision=decision,
            updated_at=utc_now_iso(),
        )
        return self.review_repository.update_review_item(updated)

    def correct_review(
        self,
        review_id: str,
        corrected_value: str,
        reason: str,
        reviewer: str,
        comment: str = "",
    ) -> ReviewItem:
        item = self.get_review_item(review_id)
        if item.status not in {ReviewStatus.PENDING, ReviewStatus.IN_REVIEW}:
            raise InvalidReviewStateError("Review can only be corrected from pending or in_review")

        correction = ReviewCorrection(
            original_value=item.entity_value,
            corrected_value=corrected_value,
            reason=reason,
            reviewer=reviewer,
            timestamp=utc_now_iso(),
        )
        decision = ReviewDecision(decision="corrected", reviewer=reviewer, timestamp=utc_now_iso(), comment=comment)
        updated = replace(
            item,
            status=ReviewStatus.CORRECTED,
            decision=decision,
            corrections=item.corrections + (correction,),
            updated_at=utc_now_iso(),
        )
        return self.review_repository.update_review_item(updated)

    def complete_review(self, review_id: str) -> ReviewItem:
        item = self.get_review_item(review_id)
        if item.status not in {ReviewStatus.APPROVED, ReviewStatus.REJECTED, ReviewStatus.CORRECTED}:
            raise InvalidReviewStateError("Review can only be completed from a final state")
        updated = replace(item, updated_at=utc_now_iso())
        return self.review_repository.update_review_item(updated)

    def list_pending_reviews(self) -> list[ReviewItem]:
        return self.review_repository.list_pending_reviews()

    def submit_feedback(self, review_id: str, metadata: Optional[Dict[str, Any]] = None) -> FeedbackRecord:
        item = self.get_review_item(review_id)
        feedback = FeedbackRecord(
            review_id=review_id,
            outcome=item.status.value,
            review_item=item.to_dict(),
            decision=item.decision,
            correction=item.corrections[-1] if item.corrections else None,
            created_at=utc_now_iso(),
            metadata=metadata or {},
        )
        return self.feedback_repository.save_feedback(review_id, feedback)
