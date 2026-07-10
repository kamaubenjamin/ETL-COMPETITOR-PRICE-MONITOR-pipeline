"""Enumerations shared by Review Runtime v1 contracts."""

from enum import Enum


class ReviewStatus(str, Enum):
    REVIEW_REQUIRED = "review_required"
    IN_REVIEW = "in_review"
    CORRECTED = "corrected"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"
    REPROCESS_REQUESTED = "reprocess_requested"
    RESOLVED = "resolved"


class ReviewerDecisionType(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    CORRECT = "correct"
    SKIP = "skip"
    REQUEST_REPROCESS = "request_reprocess"


class ReviewCaseType(str, Enum):
    VALIDATION_FAILURE = "validation_failure"
    EXTRACTION_UNCERTAINTY = "extraction_uncertainty"
    MATCHING_AMBIGUITY = "matching_ambiguity"
    DUPLICATE_DETECTION = "duplicate_detection"
    BLOCKED_CUSTOMER = "blocked_customer"
    INVALID_DATA = "invalid_data"
    EXPORT_ERROR = "export_error"
    MANUAL_ESCALATION = "manual_escalation"


class ReviewPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class SourceRuntime(str, Enum):
    DOCUMENT = "document"
    ENTITY = "entity"
    MATCHING = "matching"
    TRANSFORMS = "transforms"
    WORKFLOW = "workflow"
    REVIEW = "review"
    EXPORT = "export"


class CorrectionOperation(str, Enum):
    REPLACE = "replace"
    SET_NULL = "set_null"


class ControlledValueType(str, Enum):
    NULL = "null"
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"

