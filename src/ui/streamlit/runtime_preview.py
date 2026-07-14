"""Pure non-authoritative runtime preview labels for the operator console."""

from __future__ import annotations

from dataclasses import dataclass


PREVIEW_RUNTIME_MODES = ("local", "test", "demo", "local_api_auth")
PREVIEW_BACKENDS = ("api_default", "in_memory", "sqlite")
PREVIEW_AUTH_MODES = ("disabled", "local_demo")

_MISMATCH_MESSAGES = {
    "identity_with_disabled_auth": (
        "Preview mismatch: an identity header is selected while auth preview is disabled. "
        "The API remains authoritative."
    ),
    "missing_local_demo_identity": (
        "Preview mismatch: local demo auth is selected without an identity header. "
        "The API may require authentication."
    ),
}


@dataclass(frozen=True, slots=True)
class RuntimePreviewSelection:
    """Display-only labels that never select or construct backend services."""

    runtime_mode: str = "local"
    backend: str = "api_default"
    auth_mode: str = "disabled"

    def __post_init__(self) -> None:
        if self.runtime_mode not in PREVIEW_RUNTIME_MODES:
            raise ValueError("runtime preview mode is invalid")
        if self.backend not in PREVIEW_BACKENDS:
            raise ValueError("runtime preview backend is invalid")
        if self.auth_mode not in PREVIEW_AUTH_MODES:
            raise ValueError("runtime preview auth mode is invalid")

    def to_safe_dict(self) -> dict[str, str | bool]:
        return {
            "runtime_mode_label": self.runtime_mode,
            "backend_label": self.backend,
            "auth_mode_label": self.auth_mode,
            "authoritative": False,
            "source_of_truth": "document_intelligence_api",
        }


def runtime_preview_mismatch(
    selection: RuntimePreviewSelection,
    *,
    auth_preview_identity: str,
) -> str | None:
    """Return fixed UI guidance without deciding API authorization."""

    if selection.auth_mode == "disabled" and auth_preview_identity != "unspecified":
        return _MISMATCH_MESSAGES["identity_with_disabled_auth"]
    if selection.auth_mode == "local_demo" and auth_preview_identity == "unspecified":
        return _MISMATCH_MESSAGES["missing_local_demo_identity"]
    return None
