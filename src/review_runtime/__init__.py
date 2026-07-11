"""Review / Correction Runtime public surface."""

from src.review_runtime.models.review_item import ReviewItem
from src.review_runtime.models.review_decision import ReviewDecision
from src.review_runtime.models.review_correction import ReviewCorrection
from src.review_runtime.models.feedback_record import FeedbackRecord
from src.review_runtime.models.status import ReviewStatus as LegacyReviewStatus
from src.review_runtime.services.feedback_service import FeedbackService
from src.review_runtime.services.review_service import ReviewService
from src.review_runtime.repositories.in_memory_feedback_repository import InMemoryFeedbackRepository
from src.review_runtime.repositories.in_memory_review_repository import InMemoryReviewRepository

from .contracts import (
    ControlledValue,
    ControlledValueType,
    CorrectionOperation,
    FieldCorrection,
    ReprocessRequest,
    ReviewAuditEvent,
    ReviewCase,
    ReviewCaseType,
    ReviewPriority,
    ReviewerDecision,
    ReviewerDecisionType,
    ReviewStatus,
    SourceRuntime,
)
from .errors import ReviewRuntimeError
from .repositories import InMemoryReviewCaseRepository, ReviewCaseRepository
from .services.review_case_service import ReviewCaseService
from .services.correction_decision_service import CorrectionDecisionService
from .state_machine import (
    ALLOWED_TRANSITIONS,
    ReviewTransition,
    can_transition,
    status_for_decision,
    transition_review_case,
    transition_status,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "ControlledValue",
    "ControlledValueType",
    "CorrectionOperation",
    "CorrectionDecisionService",
    "FeedbackRecord",
    "FeedbackService",
    "FieldCorrection",
    "InMemoryFeedbackRepository",
    "InMemoryReviewCaseRepository",
    "InMemoryReviewRepository",
    "LegacyReviewStatus",
    "ReprocessRequest",
    "ReviewAuditEvent",
    "ReviewCase",
    "ReviewCaseRepository",
    "ReviewCaseService",
    "ReviewCaseType",
    "ReviewCorrection",
    "ReviewDecision",
    "ReviewItem",
    "ReviewPriority",
    "ReviewRuntimeError",
    "ReviewService",
    "ReviewerDecision",
    "ReviewerDecisionType",
    "ReviewStatus",
    "ReviewTransition",
    "SourceRuntime",
    "can_transition",
    "status_for_decision",
    "transition_review_case",
    "transition_status",
]
