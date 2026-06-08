"""Tests for EntityConcurrencyConfig — defaults, validation, and edge cases."""

import pytest

from src.entity_runtime.concurrency.config import EntityConcurrencyConfig


class TestEntityConcurrencyConfigDefaults:
    """Verify all config defaults match the architecture plan."""

    def test_version_store_defaults(self):
        config = EntityConcurrencyConfig()
        assert config.entity_version_store_enabled is False
        assert config.entity_version_store_db_path == "data/entity_version_store.db"

    def test_optimistic_locking_defaults(self):
        config = EntityConcurrencyConfig()
        assert config.optimistic_retry_max_attempts == 3
        assert config.optimistic_retry_base_delay_ms == 50
        assert config.optimistic_retry_max_delay_ms == 500
        assert config.optimistic_retry_backoff_multiplier == 2.0

    def test_pessimistic_locking_defaults(self):
        config = EntityConcurrencyConfig()
        assert config.escalation_retry_threshold == 3
        assert config.escalation_conflict_rate == 0.30
        assert config.escalation_rolling_window_minutes == 5
        assert config.escalation_cooldown_minutes == 15
        assert config.pessimistic_lock_acquire_timeout_s == 30
        assert config.pessimistic_lock_max_hold_s == 60

    def test_lease_defaults(self):
        config = EntityConcurrencyConfig()
        assert config.entity_lease_default_s == 120
        assert config.entity_lease_refresh_interval_s == 20
        assert config.entity_lease_refresh_grace_s == 10
        assert config.entity_lease_retry_max_attempts == 3
        assert config.entity_lease_retry_base_delay_ms == 100

    def test_idempotency_defaults(self):
        config = EntityConcurrencyConfig()
        assert config.entity_idempotency_retention_days == 7
        assert config.entity_idempotency_in_progress_ttl_minutes == 60
        assert config.entity_idempotency_cleanup_batch_size == 1000
        assert config.entity_idempotency_cleanup_interval_minutes == 60

    def test_frozen_dataclass(self):
        config = EntityConcurrencyConfig()
        with pytest.raises((AttributeError, TypeError)):
            config.optimistic_retry_max_attempts = 5  # type: ignore[misc]


class TestEntityConcurrencyConfigValidation:
    """Verify config validation catches invalid values."""

    def test_valid_config_returns_empty_errors(self):
        config = EntityConcurrencyConfig()
        assert config.validate() == []
        assert config.is_valid() is True

    def test_invalid_retry_max_attempts(self):
        config = EntityConcurrencyConfig(optimistic_retry_max_attempts=0)
        errors = config.validate()
        assert any("optimistic_retry_max_attempts" in e for e in errors)
        assert config.is_valid() is False

    def test_invalid_base_delay(self):
        config = EntityConcurrencyConfig(optimistic_retry_base_delay_ms=0)
        errors = config.validate()
        assert any("optimistic_retry_base_delay_ms" in e for e in errors)

    def test_invalid_max_delay_less_than_base(self):
        config = EntityConcurrencyConfig(
            optimistic_retry_base_delay_ms=500,
            optimistic_retry_max_delay_ms=100,
        )
        errors = config.validate()
        assert any("optimistic_retry_max_delay_ms" in e for e in errors)

    def test_lease_duration_too_short(self):
        config = EntityConcurrencyConfig(
            entity_lease_default_s=30,
            entity_lease_refresh_interval_s=20,
        )
        errors = config.validate()
        assert any("entity_lease_default_s" in e for e in errors)

    def test_invalid_retention_days(self):
        config = EntityConcurrencyConfig(entity_idempotency_retention_days=0)
        errors = config.validate()
        assert any("entity_idempotency_retention_days" in e for e in errors)

    def test_negative_grace(self):
        config = EntityConcurrencyConfig(entity_lease_refresh_grace_s=-1)
        errors = config.validate()
        assert any("entity_lease_refresh_grace_s" in e for e in errors)


class TestEntityConcurrencyConfigOverride:
    """Verify config can be overridden."""

    def test_override_enabled(self):
        config = EntityConcurrencyConfig(entity_version_store_enabled=True)
        assert config.entity_version_store_enabled is True

    def test_override_db_path(self):
        config = EntityConcurrencyConfig(
            entity_version_store_db_path="/custom/path/store.db"
        )
        assert config.entity_version_store_db_path == "/custom/path/store.db"

    def test_override_lease_duration(self):
        config = EntityConcurrencyConfig(entity_lease_default_s=300)
        assert config.entity_lease_default_s == 300

    def test_multiple_overrides(self):
        config = EntityConcurrencyConfig(
            optimistic_retry_max_attempts=5,
            escalation_cooldown_minutes=30,
            entity_lease_refresh_interval_s=30,
        )
        assert config.optimistic_retry_max_attempts == 5
        assert config.escalation_cooldown_minutes == 30
        assert config.entity_lease_refresh_interval_s == 30
        assert config.is_valid()