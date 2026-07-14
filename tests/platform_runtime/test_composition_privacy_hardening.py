import json

import pytest

from src.platform_runtime import (
    ApiConfig,
    AuthConfig,
    BackendConfig,
    RuntimeConfig,
    RuntimeValidationError,
    StreamlitConfig,
    compose_runtime,
)


NOW = "2026-07-14T14:00:00+00:00"


def _local_config():
    return RuntimeConfig(
        "local",
        BackendConfig("in_memory"),
        AuthConfig("disabled"),
        ApiConfig("read_only_unguarded"),
        StreamlitConfig("local_preview"),
    )


def test_unexpected_construction_failure_is_mapped_without_raw_exception(monkeypatch):
    def fail(_config):
        raise RuntimeError("token=private C:/storage/runtime.sqlite3 stack trace")

    monkeypatch.setattr("src.platform_runtime.composition.compose_runtime_document_state", fail)
    with pytest.raises(RuntimeValidationError) as raised:
        compose_runtime(_local_config(), snapshot_at=NOW)
    assert raised.value.to_dict() == {
        "code": "composition_failed",
        "field": None,
        "message": "Runtime composition could not be completed.",
    }
    serialized = json.dumps(raised.value.to_dict())
    for forbidden in ("private", "storage", "sqlite3", "stack", "token"):
        assert forbidden not in serialized.lower()


def test_safe_diagnostics_redact_path_and_identity_reference(tmp_path):
    path = tmp_path / "private" / "pilot.sqlite3"
    path.parent.mkdir()
    reference = "secret://identity/private-provider"
    config = RuntimeConfig(
        "pilot",
        BackendConfig("sqlite", sqlite_path=str(path)),
        AuthConfig(
            "authenticated",
            identity_provider="external",
            identity_provider_available=True,
            identity_provider_reference=reference,
        ),
        ApiConfig("read_only_guarded"),
        StreamlitConfig("api_preview"),
    )
    runtime = compose_runtime(config, snapshot_at=NOW)
    serialized = json.dumps(runtime.to_safe_dict(), sort_keys=True)
    assert str(path) not in serialized
    assert reference not in serialized
    assert str(path) not in repr(runtime)
    assert reference not in repr(runtime)


def test_cleanup_hook_is_safe_and_idempotent():
    runtime = compose_runtime(_local_config(), snapshot_at=NOW)
    assert runtime.close() is None
    assert runtime.close() is None

