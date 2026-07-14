"""Fixed status catalogs for governed workflow definitions and operations."""

from enum import Enum


class WorkflowDefinitionStatus(str, Enum):
    DRAFT = "draft"
    VALIDATING = "validating"
    INVALID = "invalid"
    VALID = "valid"
    TEST_READY = "test_ready"
    TESTING = "testing"
    TEST_FAILED = "test_failed"
    APPROVED = "approved"
    PUBLISHED = "published"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class WorkflowVersionStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    TEST_PASSED = "test_passed"
    APPROVED = "approved"
    PUBLISHED = "published"
    SUPERSEDED = "superseded"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class WorkflowPublicationStatus(str, Enum):
    NOT_PUBLISHED = "not_published"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class RuleStatus(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    SKIPPED = "skipped"


class OperationAvailabilityStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEPRECATED = "deprecated"

