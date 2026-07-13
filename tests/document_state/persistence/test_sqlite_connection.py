from pathlib import Path
import sqlite3

import pytest

from src.document_state.persistence import PersistenceConfig, PersistenceError
from src.document_state.persistence.sqlite import SQLiteConnectionFactory


def test_connection_requires_explicit_file_backed_sqlite_config(tmp_path):
    with pytest.raises(PersistenceError):
        SQLiteConnectionFactory(PersistenceConfig("in_memory"))
    with pytest.raises(PersistenceError):
        PersistenceConfig("sqlite", sqlite_path=":memory:")

    path = tmp_path / "document-state.sqlite3"
    factory = SQLiteConnectionFactory(PersistenceConfig("sqlite", sqlite_path=str(path)))
    with factory.transaction(write=True) as connection:
        connection.execute("CREATE TABLE probe (value TEXT NOT NULL)")
        connection.execute("INSERT INTO probe VALUES (?)", ("durable",))
    assert path.is_file()

    with factory.transaction() as connection:
        assert connection.execute("SELECT value FROM probe").fetchone()[0] == "durable"


def test_failed_transaction_rolls_back_and_connection_closes(tmp_path):
    factory = SQLiteConnectionFactory(
        PersistenceConfig("sqlite", sqlite_path=str(tmp_path / "rollback.sqlite3"))
    )
    with factory.transaction(write=True) as connection:
        connection.execute("CREATE TABLE probe (id TEXT PRIMARY KEY)")
    with pytest.raises(sqlite3.IntegrityError):
        with factory.transaction(write=True) as connection:
            connection.execute("INSERT INTO probe VALUES ('one')")
            connection.execute("INSERT INTO probe VALUES ('one')")
    with factory.transaction() as connection:
        assert connection.execute("SELECT COUNT(*) FROM probe").fetchone()[0] == 0


def test_connection_does_not_create_missing_parent_directories(tmp_path):
    path = Path(tmp_path) / "missing" / "state.sqlite3"
    factory = SQLiteConnectionFactory(PersistenceConfig("sqlite", sqlite_path=str(path)))
    with pytest.raises(PersistenceError) as raised:
        factory.connect()
    assert raised.value.code == "connection_unavailable"
