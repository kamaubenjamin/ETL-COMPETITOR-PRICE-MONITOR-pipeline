"""Shared fixtures for entity runtime concurrency tests."""
from __future__ import annotations

import os
import sqlite3
import tempfile
from typing import Any, Generator

import pytest

from src.entity_runtime.concurrency.config import EntityConcurrencyConfig, DEFAULT_CONCURRENCY_CONFIG
from src.entity_runtime.concurrency.leases import LeaseManager
from src.entity_runtime.concurrency.optimistic import OptimisticLockManager
from src.entity_runtime.concurrency.pessimistic import PessimisticLockManager
from src.entity_runtime.concurrency.guard import EntityConcurrencyGuard
from src.entity_runtime.store.idempotency import EntityIdempotencyRegistry
from src.entity_runtime.store.version_store import EntityVersionRecord, EntityVersionStore


@pytest.fixture
def db_path() -> Generator[str, None, None]:
    """Create a temporary SQLite database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def store(db_path: str) -> Generator[EntityVersionStore, None, None]:
    """Create an EntityVersionStore with schema initialized."""
    s = EntityVersionStore(db_path=db_path)
    s.initialize_schema()
    yield s
    s.close()


@pytest.fixture
def idempotency_registry(db_path: str) -> Generator[EntityIdempotencyRegistry, None, None]:
    """Create an EntityIdempotencyRegistry with schema initialized."""
    # Ensure tables exist
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS entity_idempotency (
            idempotency_key      TEXT PRIMARY KEY,
            entity_version_key   TEXT NOT NULL,
            version              INTEGER NOT NULL,
            pipeline_run_id      TEXT NOT NULL,
            status               TEXT NOT NULL DEFAULT 'in_progress',
            created_at           TEXT NOT NULL,
            completed_at         TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_entity_idempotency_cleanup
            ON entity_idempotency (status, created_at);
    """)
    conn.commit()
    conn.close()

    reg = EntityIdempotencyRegistry(db_path=db_path)
    yield reg
    reg.close()


@pytest.fixture
def config() -> EntityConcurrencyConfig:
    """Default test configuration with fast lease durations."""
    return EntityConcurrencyConfig(
        entity_version_store_enabled=True,
        entity_lease_default_s=5,
        entity_lease_refresh_interval_s=1,
        entity_lease_refresh_grace_s=1,
        entity_lease_retry_max_attempts=2,
        optimistic_retry_max_attempts=3,
        optimistic_retry_base_delay_ms=10,
        optimistic_retry_max_delay_ms=50,
        escalation_retry_threshold=2,
        escalation_cooldown_minutes=1,
    )


@pytest.fixture
def optimistic_manager(store: EntityVersionStore, config: EntityConcurrencyConfig) -> OptimisticLockManager:
    """Create an OptimisticLockManager."""
    return OptimisticLockManager(version_store=store, config=config)


@pytest.fixture
def pessimistic_manager(config: EntityConcurrencyConfig, db_path: str) -> Generator[PessimisticLockManager, None, None]:
    """Create a PessimisticLockManager with schema initialized."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entity_leases (
            entity_version_key   TEXT PRIMARY KEY,
            holder_id            TEXT NOT NULL,
            acquired_at          TEXT NOT NULL,
            expires_at           TEXT NOT NULL,
            lease_duration_s     INTEGER NOT NULL DEFAULT 120,
            last_refreshed_at    TEXT NOT NULL,
            refresh_count        INTEGER NOT NULL DEFAULT 0,
            hostname             TEXT NOT NULL DEFAULT '',
            pid                  INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    pm = PessimisticLockManager(config=config, db_path=db_path)
    yield pm
    pm.close()


@pytest.fixture
def lease_manager(config: EntityConcurrencyConfig, db_path: str) -> Generator[LeaseManager, None, None]:
    """Create a LeaseManager with schema initialized."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entity_leases (
            entity_version_key   TEXT PRIMARY KEY,
            holder_id            TEXT NOT NULL,
            acquired_at          TEXT NOT NULL,
            expires_at           TEXT NOT NULL,
            lease_duration_s     INTEGER NOT NULL DEFAULT 120,
            last_refreshed_at    TEXT NOT NULL,
            refresh_count        INTEGER NOT NULL DEFAULT 0,
            hostname             TEXT NOT NULL DEFAULT '',
            pid                  INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    lm = LeaseManager(config=config, db_path=db_path)
    yield lm
    lm.close()


@pytest.fixture
def guard(
    store: EntityVersionStore,
    optimistic_manager: OptimisticLockManager,
    pessimistic_manager: PessimisticLockManager,
    lease_manager: LeaseManager,
    idempotency_registry: EntityIdempotencyRegistry,
    config: EntityConcurrencyConfig,
) -> EntityConcurrencyGuard:
    """Create a full EntityConcurrencyGuard."""
    return EntityConcurrencyGuard(
        version_store=store,
        optimistic_manager=optimistic_manager,
        pessimistic_manager=pessimistic_manager,
        lease_manager=lease_manager,
        idempotency_registry=idempotency_registry,
        config=config,
    )


@pytest.fixture
def sample_data() -> dict[str, Any]:
    """Sample entity data for testing."""
    return {
        "name": "ACME Corp",
        "address": "123 Main St",
        "contact": "John Doe",
    }


@pytest.fixture
def sample_key() -> str:
    """Sample entity version key."""
    return "supplier:doc-1:acme-corp"