"""Configuration constants for the Workflow Runtime Locking subsystem.

These constants are the canonical defaults. They are separate from
``src/config.py`` to maintain a clean boundary for the locking module,
and can be imported directly or overridden by the main application config.
"""

# ── Lock Provider Configuration ──────────────────────────────────────

#: Primary lock provider to use: "database", "file", or "memory".
#: "database" is the recommended default for production deployments.
LOCK_PROVIDER: str = "database"

#: Default lease duration in seconds (5 minutes).
#: Must be longer than the maximum expected workflow execution time.
LOCK_DEFAULT_LEASE_S: int = 300

#: Interval in seconds between lease refresh attempts (30 seconds).
#: The lease_duration_s must be at least 3x this value.
LOCK_REFRESH_INTERVAL_S: int = 30

#: Maximum number of lock acquisition retries before raising an error.
LOCK_MAX_RETRIES: int = 3

#: Base delay in seconds between retries (exponential backoff applied).
LOCK_RETRY_DELAY_S: int = 5

#: Database table name for the workflow_locks table.
LOCK_DB_TABLE: str = "workflow_locks"

#: Directory name (relative to workspace) for file-based lock files.
LOCK_FILE_DIR: str = ".locks"

# ── Idempotency Configuration ────────────────────────────────────────

#: Whether idempotency key checking is enabled.
IDEMPOTENCY_ENABLED: bool = True

#: Number of days to keep completed idempotency keys before cleanup.
IDEMPOTENCY_KEY_TTL_DAYS: int = 7

#: Database table name for the workflow_idempotency table.
IDEMPOTENCY_DB_TABLE: str = "workflow_idempotency"

# ── Provider Priority (for LockProviderRegistry fallback chain) ──────

#: Priority value for the database lock provider (highest priority).
PRIORITY_DATABASE: int = 0

#: Priority value for the file lock provider.
PRIORITY_FILE: int = 10

#: Priority value for the memory lock provider (lowest priority).
PRIORITY_MEMORY: int = 20