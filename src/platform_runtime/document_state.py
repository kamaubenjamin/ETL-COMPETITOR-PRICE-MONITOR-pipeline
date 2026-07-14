"""Validated Document State backend composition for the platform runtime."""

from __future__ import annotations

from src.document_state import DocumentStateComposition, compose_document_state
from src.document_state.persistence import PersistenceConfig, PersistenceError

from .config import RuntimeConfig
from .errors import RuntimeErrorCode, RuntimeValidationError
from .validation import assert_runtime_config_valid


def compose_runtime_document_state(config: RuntimeConfig) -> DocumentStateComposition:
    """Compose exactly the validated backend without fallback."""

    safe_config = assert_runtime_config_valid(config)
    assert safe_config.backend is not None
    try:
        persistence = PersistenceConfig(
            backend=safe_config.backend.mode.value,
            sqlite_path=safe_config.backend.sqlite_path,
        )
        return compose_document_state(persistence)
    except PersistenceError:
        raise RuntimeValidationError(
            RuntimeErrorCode.COMPOSITION_FAILED,
            field="backend",
        ) from None
