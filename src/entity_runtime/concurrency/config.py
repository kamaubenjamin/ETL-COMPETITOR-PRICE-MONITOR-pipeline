"""EntityConcurrencyConfig — all configurable parameters for entity concurrency hardening."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True, slots=True)
class EntityConcurrencyConfig:
    """Configuration for entity concurrency hardening.

    All parameters have sensible defaults per the architecture plan.
    Override via environment variables in production deployments.
    """

    # ==================================================================
    # Entity Version Store settings
    # ==================================================================
    entity_version_store_enabled: bool = False
    """Opt-in feature flag. When False, all version store interaction is skipped."""

    entity_version_store_db_path: str = "data/entity_version_store.db"
    """SQLite database path for the entity version store."""

    # ==================================================================
    # Optimistic locking parameters
    # ==================================================================
    optimistic_retry_max_attempts: int = 3
    """Maximum CAS retry attempts before raising EntityConflictError."""

    optimistic_retry_base_delay_ms: int = 50
    """Base delay for exponential backoff (milliseconds)."""

    optimistic_retry_max_delay_ms: int = 500
    """Maximum delay for exponential backoff (milliseconds)."""

    optimistic_retry_backoff_multiplier: float = 2.0
    """Multiplier for exponential backoff per attempt."""

    # ==================================================================
    # Pessimistic lock escalation thresholds
    # ==================================================================
    escalation_retry_threshold: int = 3
    """After this many consecutive CAS failures, escalate to pessimistic."""

    escalation_conflict_rate: float = 0.30
    """If >30% of writes in rolling window conflict, escalate."""

    escalation_rolling_window_minutes: int = 5
    """Rolling window for conflict rate calculation."""

    escalation_cooldown_minutes: int = 15
    """Time before auto-de-escalating to optimistic locking."""

    pessimistic_lock_acquire_timeout_s: int = 30
    """Timeout for acquiring a pessimistic lock (seconds)."""

    pessimistic_lock_max_hold_s: int = 60
    """Maximum time any pessimistic lock can be held (seconds)."""

    # ==================================================================
    # Execution lease parameters
    # ==================================================================
    entity_lease_default_s: int = 120
    """Default lease duration in seconds (2 minutes)."""

    entity_lease_refresh_interval_s: int = 20
    """Lease refresh interval in seconds."""

    entity_lease_refresh_grace_s: int = 10
    """Grace period before considering a lease expired (seconds)."""

    entity_lease_retry_max_attempts: int = 3
    """Maximum retry attempts for lease acquisition."""

    entity_lease_retry_base_delay_ms: int = 100
    """Base delay for lease acquisition retry (milliseconds)."""

    # ==================================================================
    # Idempotency retention and cleanup settings
    # ==================================================================
    entity_idempotency_retention_days: int = 7
    """Keep completed/failed idempotency keys for 7 days."""

    entity_idempotency_in_progress_ttl_minutes: int = 60
    """Expire in-progress keys after 60 minutes."""

    entity_idempotency_cleanup_batch_size: int = 1000
    """Delete up to 1000 keys per cleanup cycle."""

    entity_idempotency_cleanup_interval_minutes: int = 60
    """Run cleanup every 60 minutes."""

    # ==================================================================
    # Validation
    # ==================================================================

    def validate(self) -> list[str]:
        """Validate configuration consistency. Returns list of error messages (empty if valid)."""
        errors: list[str] = []

        if self.optimistic_retry_max_attempts < 1:
            errors.append("optimistic_retry_max_attempts must be >= 1")

        if self.optimistic_retry_base_delay_ms < 1:
            errors.append("optimistic_retry_base_delay_ms must be >= 1")

        if self.optimistic_retry_max_delay_ms < self.optimistic_retry_base_delay_ms:
            errors.append("optimistic_retry_max_delay_ms must be >= optimistic_retry_base_delay_ms")

        if self.entity_lease_default_s < self.entity_lease_refresh_interval_s * 3:
            errors.append(
                "entity_lease_default_s must be >= 3 * entity_lease_refresh_interval_s "
                f"({self.entity_lease_refresh_interval_s * 3}s)"
            )

        if self.entity_lease_refresh_grace_s < 0:
            errors.append("entity_lease_refresh_grace_s must be >= 0")

        if self.entity_idempotency_retention_days < 1:
            errors.append("entity_idempotency_retention_days must be >= 1")

        return errors

    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return len(self.validate()) == 0


# Default singleton for convenient import
DEFAULT_CONCURRENCY_CONFIG = EntityConcurrencyConfig()