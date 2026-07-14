"""Top-level internal service composition for validated runtime modes."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.document_state import DocumentStateComposition
from src.document_state.lifecycle import LifecycleAdvancementService
from src.workflow_runtime.query_facade import WorkflowQueryFacadePort

from .config import RuntimeConfig
from .document_state import compose_runtime_document_state
from .errors import RuntimeErrorCode, RuntimeValidationError
from .lifecycle import compose_lifecycle_service
from .query_facade import compose_query_facade
from .validation import assert_runtime_config_valid
from .writers import RuntimeWriterServices, compose_writer_services


@dataclass(frozen=True, slots=True)
class RuntimeComposition:
    """Owned internal runtime services; API and UI activation are intentionally absent."""

    runtime_config: RuntimeConfig = field(repr=False)
    document_state: DocumentStateComposition = field(repr=False)
    lifecycle: LifecycleAdvancementService = field(repr=False)
    writers: RuntimeWriterServices | None = field(repr=False)
    query_facade: WorkflowQueryFacadePort = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.runtime_config, RuntimeConfig):
            raise RuntimeValidationError(RuntimeErrorCode.COMPOSITION_FAILED)
        if not isinstance(self.document_state, DocumentStateComposition):
            raise RuntimeValidationError(RuntimeErrorCode.COMPOSITION_FAILED)
        if not isinstance(self.lifecycle, LifecycleAdvancementService):
            raise RuntimeValidationError(RuntimeErrorCode.COMPOSITION_FAILED)
        if self.writers is not None and not isinstance(self.writers, RuntimeWriterServices):
            raise RuntimeValidationError(RuntimeErrorCode.COMPOSITION_FAILED)
        if not isinstance(self.query_facade, WorkflowQueryFacadePort):
            raise RuntimeValidationError(RuntimeErrorCode.COMPOSITION_FAILED)
        backend = self.runtime_config.backend
        if backend is None or backend.mode.value != self.document_state.backend:
            raise RuntimeValidationError(RuntimeErrorCode.COMPOSITION_FAILED, field="backend")
        if self.runtime_config.writers_enabled != (self.writers is not None):
            raise RuntimeValidationError(RuntimeErrorCode.COMPOSITION_FAILED)

    @property
    def backend(self) -> str:
        return self.document_state.backend

    @property
    def is_durable(self) -> bool:
        return self.document_state.is_durable

    def to_safe_dict(self) -> dict[str, object]:
        """Return a JSON-compatible descriptor without paths or repository details."""

        return {
            "config": self.runtime_config.to_redacted_dict(),
            "backend": self.backend,
            "is_durable": self.is_durable,
            "lifecycle_composed": True,
            "writers_composed": self.writers is not None,
            "query_facade_composed": True,
            "api_composed": False,
            "streamlit_composed": False,
        }

    def close(self) -> None:
        """Reserved ownership hook; current repositories use short-lived resources."""


def compose_runtime(config: RuntimeConfig, *, snapshot_at: str) -> RuntimeComposition:
    """Validate first, then build the internal service graph without partial output."""

    safe_config = assert_runtime_config_valid(config)
    try:
        document_state = compose_runtime_document_state(safe_config)
        lifecycle = compose_lifecycle_service(document_state)
        writers = (
            compose_writer_services(document_state, lifecycle)
            if safe_config.writers_enabled
            else None
        )
        query_facade = compose_query_facade(document_state, snapshot_at=snapshot_at)
    except RuntimeValidationError:
        raise
    except Exception:
        raise RuntimeValidationError(RuntimeErrorCode.COMPOSITION_FAILED) from None
    return RuntimeComposition(
        runtime_config=safe_config,
        document_state=document_state,
        lifecycle=lifecycle,
        writers=writers,
        query_facade=query_facade,
    )
