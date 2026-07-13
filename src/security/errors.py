"""Stable privacy-safe security errors."""

from __future__ import annotations

from enum import Enum


class SecurityErrorCode(str, Enum):
    INVALID_CONTRACT = "invalid_contract"
    INVALID_CONFIGURATION = "invalid_configuration"
    AUTHENTICATION_REQUIRED = "authentication_required"
    AUTHORIZATION_DENIED = "authorization_denied"
    INTERNAL_ERROR = "internal_error"


_MESSAGES = {
    SecurityErrorCode.INVALID_CONTRACT: "Security contract is invalid.",
    SecurityErrorCode.INVALID_CONFIGURATION: "Security configuration is invalid.",
    SecurityErrorCode.AUTHENTICATION_REQUIRED: "Authentication is required.",
    SecurityErrorCode.AUTHORIZATION_DENIED: "Access is denied.",
    SecurityErrorCode.INTERNAL_ERROR: "Security operation could not be completed.",
}


class SecurityError(Exception):
    """Exception exposing only a stable code and fixed safe message."""

    def __init__(self, code: SecurityErrorCode | str) -> None:
        try:
            self.code = code if isinstance(code, SecurityErrorCode) else SecurityErrorCode(code)
        except (TypeError, ValueError):
            self.code = SecurityErrorCode.INTERNAL_ERROR
        self.message = _MESSAGES[self.code]
        super().__init__(self.message)

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code.value, "message": self.message}

