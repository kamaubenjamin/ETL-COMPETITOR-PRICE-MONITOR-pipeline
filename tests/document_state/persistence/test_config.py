from dataclasses import FrozenInstanceError

import pytest

from src.document_state.persistence import (
    PersistenceConfig,
    PersistenceError,
    require_active_backend,
)


def test_backend_selection_is_explicit_and_config_is_immutable():
    config = PersistenceConfig("in_memory")
    assert config.backend == "in_memory"
    assert config.is_active and not config.is_deferred
    with pytest.raises(FrozenInstanceError):
        config.backend = "sqlite"


def test_unknown_backend_is_rejected_safely():
    with pytest.raises(PersistenceError) as raised:
        PersistenceConfig("automatic")
    assert raised.value.code == "invalid_backend"
    assert "automatic" not in str(raised.value)


@pytest.mark.parametrize("path", [None, "", ":memory:", " spaced.db "])
def test_sqlite_requires_an_explicit_file_path(path):
    with pytest.raises(PersistenceError) as raised:
        PersistenceConfig("sqlite", sqlite_path=path)
    assert raised.value.code == "invalid_backend"
    assert raised.value.field == "sqlite_path"


def test_sqlite_config_is_json_compatible_and_does_not_create_files(tmp_path):
    path = str(tmp_path / "document-state.db")
    config = PersistenceConfig("sqlite", sqlite_path=path, sqlite_busy_timeout_ms=2500)
    assert config.to_dict() == {
        "backend": "sqlite",
        "sqlite_path": path,
        "sqlite_busy_timeout_ms": 2500,
        "is_active": True,
        "is_deferred": False,
    }
    assert not (tmp_path / "document-state.db").exists()


def test_future_postgres_is_described_but_cannot_be_activated():
    config = PersistenceConfig("future_postgres")
    assert config.is_deferred and not config.is_active
    with pytest.raises(PersistenceError) as raised:
        require_active_backend(config)
    assert raised.value.code == "invalid_backend"
