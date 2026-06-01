from src.review_runtime.contracts.review_request import ReviewRequest
from src.review_runtime.exceptions import InvalidReviewStateError
from src.review_runtime.models.status import ReviewStatus
from src.review_runtime.repositories.in_memory_feedback_repository import InMemoryFeedbackRepository
from src.review_runtime.repositories.in_memory_review_repository import InMemoryReviewRepository
from src.review_runtime.services.feedback_service import FeedbackService
from src.review_runtime.services.review_service import ReviewService


def test_create_review_item_below_threshold_is_pending():
    review_repo = InMemoryReviewRepository()
    feedback_repo = InMemoryFeedbackRepository()
    service = ReviewService(review_repo, feedback_repo)

    request = ReviewRequest(
        document_id="doc-1",
        entity_type="customer",
        entity_value="Acme Corp",
        confidence=0.65,
        metadata={"source": "matching"},
    )

    review_item = service.create_review(request)

    assert review_item.status == ReviewStatus.PENDING
    assert review_item.metadata["routing"] == "required_review"
    assert review_repo.get_review_item(review_item.review_id) is not None


def test_create_review_item_above_auto_approve_threshold_is_approved():
    review_repo = InMemoryReviewRepository()
    feedback_repo = InMemoryFeedbackRepository()
    service = ReviewService(review_repo, feedback_repo)

    request = ReviewRequest(
        document_id="doc-1",
        entity_type="line_item",
        entity_value="Widget A",
        confidence=0.98,
    )

    review_item = service.create_review(request)

    assert review_item.status == ReviewStatus.APPROVED
    assert review_item.metadata["routing"] == "auto_approved"


def test_assign_review_moves_status_to_in_review():
    review_repo = InMemoryReviewRepository()
    feedback_repo = InMemoryFeedbackRepository()
    service = ReviewService(review_repo, feedback_repo)

    request = ReviewRequest(
        document_id="doc-2",
        entity_type="supplier",
        entity_value="Global Supplies",
        confidence=0.5,
    )
    item = service.create_review(request)
    assigned = service.assign_review(item.review_id, reviewer="alice")

    assert assigned.status == ReviewStatus.IN_REVIEW
    # Tolerate identical timestamps due to precision; ensure updated is not earlier
    assert assigned.updated_at >= assigned.created_at


def test_approve_review_sets_status_and_decision():
    review_repo = InMemoryReviewRepository()
    feedback_repo = InMemoryFeedbackRepository()
    service = ReviewService(review_repo, feedback_repo)

    request = ReviewRequest(
        document_id="doc-3",
        entity_type="customer",
        entity_value="Retail Ltd",
        confidence=0.6,
    )
    item = service.create_review(request)
    approved = service.approve_review(item.review_id, reviewer="bob", comment="Confirmed match")

    assert approved.status == ReviewStatus.APPROVED
    assert approved.decision is not None
    assert approved.decision.decision == "approved"
    assert approved.decision.comment == "Confirmed match"


def test_reject_review_sets_status_and_decision():
    review_repo = InMemoryReviewRepository()
    feedback_repo = InMemoryFeedbackRepository()
    service = ReviewService(review_repo, feedback_repo)

    request = ReviewRequest(
        document_id="doc-4",
        entity_type="customer",
        entity_value="Unknown Corp",
        confidence=0.4,
    )
    item = service.create_review(request)
    rejected = service.reject_review(item.review_id, reviewer="carol", comment="Not a match")

    assert rejected.status == ReviewStatus.REJECTED
    assert rejected.decision is not None
    assert rejected.decision.decision == "rejected"


def test_correct_review_records_correction_and_status():
    review_repo = InMemoryReviewRepository()
    feedback_repo = InMemoryFeedbackRepository()
    service = ReviewService(review_repo, feedback_repo)

    request = ReviewRequest(
        document_id="doc-5",
        entity_type="line_item",
        entity_value="Widget B",
        confidence=0.55,
    )
    item = service.create_review(request)
    corrected = service.correct_review(
        review_id=item.review_id,
        corrected_value="Widget B - Large",
        reason="Missing size detail",
        reviewer="dave",
        comment="Corrected product description",
    )

    assert corrected.status == ReviewStatus.CORRECTED
    assert corrected.decision is not None
    assert corrected.decision.decision == "corrected"
    assert len(corrected.corrections) == 1
    assert corrected.corrections[0].corrected_value == "Widget B - Large"


def test_submit_feedback_persists_feedback_record():
    review_repo = InMemoryReviewRepository()
    feedback_repo = InMemoryFeedbackRepository()
    service = ReviewService(review_repo, feedback_repo)

    request = ReviewRequest(
        document_id="doc-6",
        entity_type="supplier",
        entity_value="Test Vendor",
        confidence=0.4,
    )
    item = service.create_review(request)
    rejected = service.reject_review(item.review_id, reviewer="eva", comment="Does not match vendor")
    feedback = service.submit_feedback(rejected.review_id)

    assert feedback.review_id == rejected.review_id
    assert feedback.outcome == ReviewStatus.REJECTED.value
    assert feedback.review_item["status"] == ReviewStatus.REJECTED.value


def test_invalid_transition_raises_error():
    review_repo = InMemoryReviewRepository()
    feedback_repo = InMemoryFeedbackRepository()
    service = ReviewService(review_repo, feedback_repo)

    request = ReviewRequest(
        document_id="doc-7",
        entity_type="customer",
        entity_value="Acme Ltd",
        confidence=0.98,
    )
    item = service.create_review(request)

    try:
        service.assign_review(item.review_id, reviewer="frank")
        assert False, "Expected InvalidReviewStateError"
    except InvalidReviewStateError:
        assert True
