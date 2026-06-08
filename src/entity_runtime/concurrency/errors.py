"""Exception hierarchy for entity concurrency hardening — 8 exception types.

All exceptions inherit from RuntimeError and carry structured attributes
for programmatic handling and logging.
"""


class EntityConflictError(RuntimeError):
    """CAS version mismatch — another writer committed a newer version.

    Attributes:
        entity_version_key: The entity key that experienced the conflict.
        expected_version: The version the writer expected.
        actual_version: The current version in the store.
    """

    def __init__(
        self,
        entity_version_key: str = "",
        expected_version: int = 0,
        actual_version: int = 0,
        message: str = "",
    ) -> None:
        self.entity_version_key = entity_version_key
        self.expected_version = expected_version
        self.actual_version = actual_version
        if not message:
            message = (
                f"Entity conflict on {entity_version_key}: "
                f"expected version {expected_version}, actual version {actual_version}"
            )
        super().__init__(message)


class EntityCorruptionError(RuntimeError):
    """Checksum mismatch — data corruption detected on read or write.

    Attributes:
        entity_version_key: The entity key with the corruption.
        expected_checksum: The checksum that was expected.
        actual_checksum: The checksum that was computed.
    """

    def __init__(
        self,
        entity_version_key: str = "",
        expected_checksum: str = "",
        actual_checksum: str = "",
        message: str = "",
    ) -> None:
        self.entity_version_key = entity_version_key
        self.expected_checksum = expected_checksum
        self.actual_checksum = actual_checksum
        if not message:
            message = (
                f"Data corruption detected on {entity_version_key}: "
                f"expected checksum {expected_checksum[:16]}... "
                f"actual checksum {actual_checksum[:16]}..."
            )
        super().__init__(message)


class EntityLeaseError(RuntimeError):
    """Lease acquisition or refresh failure.

    Attributes:
        entity_version_key: The entity key for the failed lease operation.
        holder_id: The current lease holder (empty if unknown).
    """

    def __init__(
        self,
        entity_version_key: str = "",
        holder_id: str = "",
        message: str = "",
    ) -> None:
        self.entity_version_key = entity_version_key
        self.holder_id = holder_id
        if not message:
            message = (
                f"Lease error on {entity_version_key}: "
                f"current holder={holder_id}" if holder_id else f"Lease error on {entity_version_key}"
            )
        super().__init__(message)


class EntityLeaseLostError(EntityLeaseError):
    """Lease expired during a write operation — another worker may have acquired it.

    Attributes:
        entity_version_key: The entity key whose lease was lost.
        holder_id: The holder that lost the lease.
    """

    def __init__(
        self,
        entity_version_key: str = "",
        holder_id: str = "",
        message: str = "",
    ) -> None:
        if not message:
            message = f"Lease lost for {entity_version_key}: holder={holder_id}"
        super().__init__(
            entity_version_key=entity_version_key,
            holder_id=holder_id,
            message=message,
        )


class EntityLockTimeoutError(RuntimeError):
    """Pessimistic lock acquisition exceeded the configured timeout.

    Attributes:
        entity_version_key: The entity key that timed out.
        timeout_s: The timeout that was exceeded (seconds).
    """

    def __init__(
        self,
        entity_version_key: str = "",
        timeout_s: int = 0,
        message: str = "",
    ) -> None:
        self.entity_version_key = entity_version_key
        self.timeout_s = timeout_s
        if not message:
            message = (
                f"Lock acquisition timeout for {entity_version_key}: "
                f"exceeded {timeout_s}s"
            )
        super().__init__(message)


class EntityDeadlockError(RuntimeError):
    """Deadlock detected during pessimistic lock acquisition.

    Attributes:
        entity_version_key: The entity key involved in the deadlock.
        held_locks: List of entity keys held by this writer.
        attempted_lock: The lock that could not be acquired.
    """

    def __init__(
        self,
        entity_version_key: str = "",
        held_locks: list[str] | None = None,
        attempted_lock: str = "",
        message: str = "",
    ) -> None:
        self.entity_version_key = entity_version_key
        self.held_locks = held_locks or []
        self.attempted_lock = attempted_lock
        if not message:
            message = (
                f"Deadlock detected for {entity_version_key}: "
                f"held={self.held_locks}, attempted={attempted_lock}"
            )
        super().__init__(message)


class EntityDuplicateWriteError(RuntimeError):
    """Idempotency key collision — duplicate write detected.

    Attributes:
        idempotency_key: The duplicate idempotency key.
        entity_version_key: The entity key being written.
        existing_version: The version that was already written.
        existing_run: The pipeline_run_id of the original write.
    """

    def __init__(
        self,
        idempotency_key: str = "",
        entity_version_key: str = "",
        existing_version: int = 0,
        existing_run: str = "",
        message: str = "",
    ) -> None:
        self.idempotency_key = idempotency_key
        self.entity_version_key = entity_version_key
        self.existing_version = existing_version
        self.existing_run = existing_run
        if not message:
            message = (
                f"Duplicate write detected: key={idempotency_key[:16]}... "
                f"entity={entity_version_key}, "
                f"existing_version={existing_version}, "
                f"existing_run={existing_run}"
            )
        super().__init__(message)


class EntityStoreUnavailableError(RuntimeError):
    """Entity version store connection failure — store is unavailable.

    Attributes:
        db_path: The database path that could not be connected.
        operation: The operation that was attempted when the failure occurred.
    """

    def __init__(
        self,
        db_path: str = "",
        operation: str = "",
        message: str = "",
    ) -> None:
        self.db_path = db_path
        self.operation = operation
        if not message:
            message = f"Entity version store unavailable: db={db_path}, operation={operation}"
        super().__init__(message)