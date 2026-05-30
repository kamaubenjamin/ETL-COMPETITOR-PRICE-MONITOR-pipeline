# Review Runtime Implementation

## Purpose

Review Runtime v1 implements a human-in-the-loop review layer for the Intelligent Document Processing Platform. It creates review tasks from low-confidence matching results, manages review status transitions, captures reviewer decisions and corrections, and generates structured feedback records.

## Runtime Structure

The Review Runtime package is located at `src/review_runtime` and contains:

- `models/` — domain models for review items, decisions, corrections, and feedback.
- `contracts/` — runtime contracts for review requests and repository interfaces.
- `services/` — business services implementing review lifecycle and feedback capture.
- `repositories/` — in-memory repository implementations for review items and feedback.
- `exceptions/` — runtime-specific exception types.
- `tests/` — unit and integration tests.

## Components Implemented

### Models
- `ReviewItem`
- `ReviewDecision`
- `ReviewCorrection`
- `ReviewStatus`
- `FeedbackRecord`

### Contracts
- `ReviewRepository`
- `FeedbackRepository`
- `ReviewRequest`

### Repositories
- `InMemoryReviewRepository`
- `InMemoryFeedbackRepository`

### Services
- `ReviewService`
- `FeedbackService`

## Contracts

The Review Runtime defines explicit repository interfaces so implementation details remain pluggable:

- `ReviewRepository` manages review item persistence and listing.
- `FeedbackRepository` stores feedback records keyed by review item.
- `ReviewRequest` is the integration contract used by workflows to create review items.

## Services

The `ReviewService` implements the review lifecycle:

- `create_review()` — creates review items and routes them based on configured confidence thresholds
- `assign_review()` — moves a review from `PENDING` to `IN_REVIEW`
- `approve_review()` — marks review items as `APPROVED`
- `reject_review()` — marks review items as `REJECTED`
- `correct_review()` — records corrections and moves items to `CORRECTED`
- `complete_review()` — finalizes reviews in terminal states
- `submit_feedback()` — generates structured feedback records for persistence

The `FeedbackService` builds and saves feedback payloads from review items, decisions, and corrections.

## State Model

Review items transition through the following states:

- `PENDING` — awaiting assignment or review
- `IN_REVIEW` — actively being reviewed
- `APPROVED` — accepted without correction
- `REJECTED` — declined as not matching
- `CORRECTED` — reviewer supplied a correction

The runtime enforces valid transitions and raises `InvalidReviewStateError` for invalid state changes.

## Integration Points

Review Runtime is callable by downstream workflows through the `ReviewService` and `ReviewRequest` contract. A matching result can be evaluated and routed to review by creating a `ReviewRequest` and passing it into `ReviewService.create_review()`.

Integration is intentionally loose:

- Review Runtime does not perform extraction or matching.
- It does not orchestrate workflows directly.
- It exposes repository interfaces so persistence can evolve without changing service logic.

## Runtime Boundaries

Review Runtime depends on:

- `Matching Runtime` for low-confidence review candidates
- `Workflow Runtime` for stage invocation and context
- `Entity Runtime` indirectly through review item payloads

Review Runtime must not:

- parse raw documents
- perform entity extraction
- perform matching calculations
- own workflow orchestration

## Example Usage

A downstream workflow can create a review item from a match result:

```python
from src.review_runtime.contracts.review_request import ReviewRequest
from src.review_runtime.repositories.in_memory_review_repository import InMemoryReviewRepository
from src.review_runtime.repositories.in_memory_feedback_repository import InMemoryFeedbackRepository
from src.review_runtime.services.review_service import ReviewService

review_repo = InMemoryReviewRepository()
feedback_repo = InMemoryFeedbackRepository()
service = ReviewService(review_repo, feedback_repo)

request = ReviewRequest(
    document_id="doc-123",
    entity_type="customer",
    entity_value="Acme Corp",
    confidence=0.65,
    metadata={"source": "matching"},
)
item = service.create_review(request)
```

## Files Added

- `src/review_runtime/__init__.py`
- `src/review_runtime/models/review_item.py`
- `src/review_runtime/models/review_decision.py`
- `src/review_runtime/models/review_correction.py`
- `src/review_runtime/models/feedback_record.py`
- `src/review_runtime/models/status.py`
- `src/review_runtime/contracts/repository.py`
- `src/review_runtime/contracts/review_request.py`
- `src/review_runtime/services/review_service.py`
- `src/review_runtime/services/feedback_service.py`
- `src/review_runtime/repositories/in_memory_review_repository.py`
- `src/review_runtime/repositories/in_memory_feedback_repository.py`
- `src/review_runtime/exceptions/__init__.py`
- `src/review_runtime/tests/test_review_service.py`
