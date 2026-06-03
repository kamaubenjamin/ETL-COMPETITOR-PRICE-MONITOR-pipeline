"""Custom exception types for the Workflow Runtime Locking subsystem.

Each exception carries informative attributes that callers can use for
retry decisions, logging, and monitoring.

Exception Hierarchy
-------------------
Exception
├── LockAcquisitionError      — lock could not be acquired
├── IdempotencyRejectionError — idempotency key already processed
├── LockProviderError         — unrecoverable provider error
└── LeaseRefreshError         — lease refresh failure (non-fatal)
"""


class LockAcquisitionError(Exception):
    """Raised when an execution lock cannot be acquired.

    The caller can use ``expires_at`` to decide when to retry.

    Attributes
    ----------
    lock_id:
        The ``workflow_id`` for which the lock was requested.
    current_holder_id:
        The ``holder_id`` of the current lock owner, if known.
    expires_at:
        ISO-8601 timestamp when the current lock lease expires. The
        caller may retry after this time.
    """

    def __init__(
        self,
        lock_id: str,
        current_holder_id: str | None = None,
        expires_at: str | None = None,
        *,
        message: str | None = None,
    ) -> None:
        if message is None:
            parts = [f"Lock acquisition failed for lock_id={lock_id!r}"]
            if current_holder_id:
                parts.append(f"currently held by {current_holder_id!r}")
            if expires_at:
                parts.append(f"expires at {expires_at}")
            message = "; ".join(parts)
        super().__init__(message)
        self.lock_id = lock_id
        self.current_holder_id = current_holder_id
        self.expires_at = expires_at


class IdempotencyRejectionError(Exception):
    """Raised when an idempotency key has already been processed.

    Attributes
    ----------
    idempotency_key:
        The idempotency key that was rejected.
    existing_status:
        The status of the existing run (e.g. ``"completed"``, ``"failed"``).
    existing_pipeline_run_id:
        The ``pipeline_run_id`` of the run that claimed this key.
    """

    def __init__(
        self,
        idempotency_key: str,
        existing_status: str,
        existing_pipeline_run_id: str,
        *,
        message: str | None = None,
    ) -> None:
        if message is None:
            message = (
                f"Idempotency key {idempotency_key!r} already processed: "
                f"status={existing_status!r}, "
                f"pipeline_run_id={existing_pipeline_run_id!r}"
            )
        super().__init__(message)
        self.idempotency_key = idempotency_key
        self.existing_status = existing_status
        self.existing_pipeline_run_id = existing_pipeline_run_id


class LockProviderError(Exception):
    """Raised when a lock provider encounters an unrecoverable error.

    Examples: database connection failure, disk full, permission denied.

    Attributes
    ----------
    provider_name:
        The name of the provider that raised the error.
    original_exception:
        The original exception that caused this error, if any.
    """

    def __init__(
        self,
        provider_name: str,
        original_exception: Exception | None = None,
        *,
        message: str | None = None,
    ) -> None:
        if message is None:
            message = f"Lock provider {provider_name!r} encountered an error"
            if original_exception:
                message += f": {original_exception}"
        super().__init__(message)
        self.provider_name = provider_name
        self.original_exception = original_exception


class LeaseRefreshError(Exception):
    """Raised when a lease refresh fails.

    This is a **non-fatal** error — execution continues with a warning.
    The last successful refresh timestamp is used for stale detection.

    Attributes
    ----------
    lock_id:
        The ``workflow_id`` whose lease refresh failed.
    holder_id:
        The ``holder_id`` of the lock owner.
    original_exception:
        The original exception that caused the refresh failure, if any.
    """

    def __init__(
        self,
        lock_id: str,
        holder_id: str,
        original_exception: Exception | None = None,
        *,
        message: str | None = None,
    ) -> None:
        if message is None:
            message = (
                f"Lease refresh failed for lock_id={lock_id!r}, "
                f"holder_id={holder_id!r}"
            )
            if original_exception:
                message += f": {original_exception}"
        super().__init__(message)
        self.lock_id = lock_id
        self.holder_id = holder_id
        self.original_exception = original_exception