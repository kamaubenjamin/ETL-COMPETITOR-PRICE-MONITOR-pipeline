"""File-backed SQLite connection and transaction management."""

from __future__ import annotations

from contextlib import contextmanager
import sqlite3
from typing import Iterator

from ..config import PersistenceBackend, PersistenceConfig, require_active_backend
from ..errors import PersistenceError


class SQLiteConnectionFactory:
    """Open short-lived configured connections to one explicit SQLite file."""

    def __init__(self, config: PersistenceConfig) -> None:
        safe = require_active_backend(config)
        if safe.backend != PersistenceBackend.SQLITE.value or safe.sqlite_path is None:
            raise PersistenceError("invalid_backend", field="backend")
        self._path = safe.sqlite_path
        self._timeout_seconds = safe.sqlite_busy_timeout_ms / 1000
        self._busy_timeout_ms = safe.sqlite_busy_timeout_ms

    def connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(
                self._path,
                timeout=self._timeout_seconds,
                isolation_level=None,
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(f"PRAGMA busy_timeout = {self._busy_timeout_ms}")
            connection.execute("PRAGMA journal_mode = WAL")
            return connection
        except (OSError, sqlite3.Error):
            raise PersistenceError("connection_unavailable") from None

    @contextmanager
    def transaction(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield connection
            connection.commit()
        except PersistenceError:
            connection.rollback()
            raise
        except sqlite3.IntegrityError:
            connection.rollback()
            raise
        except sqlite3.Error:
            connection.rollback()
            raise PersistenceError("transaction_failed") from None
        finally:
            connection.close()
