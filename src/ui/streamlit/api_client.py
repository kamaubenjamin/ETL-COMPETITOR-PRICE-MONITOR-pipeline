"""Small GET-only client for Document Intelligence API preview mode."""

from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


API_VERSION = "v1"
_ENVELOPE_FIELDS = {"success", "data", "error", "metadata", "api_version", "request_id"}
AUTH_PREVIEW_IDENTITIES = (
    "unspecified",
    "anonymous",
    "viewer",
    "reviewer",
    "tenant-admin",
    "platform-admin",
    "service-account",
)


class APIClientError(Exception):
    """Privacy-safe client or remote API failure."""

    def __init__(self, code: str, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


Transport = Callable[[Request, float], tuple[int, bytes]]


def _default_transport(request: Request, timeout: float) -> tuple[int, bytes]:
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()
    except (URLError, OSError, TimeoutError) as exc:
        raise APIClientError("api_unavailable", "Document Intelligence API is unavailable.") from exc


class DocumentIntelligenceAPIClient:
    """Read-only HTTP adapter that accepts only the standard v1 envelope."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 3.0,
        transport: Transport | None = None,
        auth_preview_identity: str = "unspecified",
    ) -> None:
        parsed = urlparse(base_url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("API base URL must be an HTTP(S) origin without credentials")
        if timeout <= 0 or timeout > 30:
            raise ValueError("timeout must be between 0 and 30 seconds")
        if auth_preview_identity not in AUTH_PREVIEW_IDENTITIES:
            raise ValueError("auth preview identity is invalid")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._transport = transport or _default_transport
        self.auth_preview_identity = auth_preview_identity

    def get(self, path: str, *, params: dict[str, str | int | None] | None = None) -> Any:
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("API path must be absolute")
        query = urlencode({key: value for key, value in (params or {}).items() if value is not None})
        url = f"{self.base_url}{path}" + (f"?{query}" if query else "")
        headers = {"Accept": "application/json"}
        if self.auth_preview_identity != "unspecified":
            headers["X-Local-Identity"] = self.auth_preview_identity
        request = Request(url, method="GET", headers=headers)
        status_code, body = self._transport(request, self.timeout)
        try:
            envelope = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise APIClientError("invalid_response", "API returned an invalid response.", status_code=status_code) from exc
        return self._parse_envelope(envelope, status_code=status_code)

    @staticmethod
    def _parse_envelope(envelope: Any, *, status_code: int) -> Any:
        if not isinstance(envelope, dict) or set(envelope) != _ENVELOPE_FIELDS:
            raise APIClientError("invalid_response", "API response envelope is invalid.", status_code=status_code)
        if not isinstance(envelope["success"], bool) or envelope["api_version"] != API_VERSION:
            raise APIClientError("invalid_response", "API response envelope is invalid.", status_code=status_code)
        if not isinstance(envelope["request_id"], str) or not isinstance(envelope["metadata"], dict):
            raise APIClientError("invalid_response", "API response envelope is invalid.", status_code=status_code)
        if envelope["success"]:
            if envelope["error"] is not None or status_code >= 400:
                raise APIClientError("invalid_response", "API response envelope is invalid.", status_code=status_code)
            return deepcopy(envelope["data"])
        error = envelope["error"]
        if envelope["data"] is not None or not isinstance(error, dict):
            raise APIClientError("invalid_response", "API response envelope is invalid.", status_code=status_code)
        code = error.get("code")
        message = error.get("message")
        if not isinstance(code, str) or not isinstance(message, str):
            raise APIClientError("invalid_response", "API response envelope is invalid.", status_code=status_code)
        raise APIClientError(code, message, status_code=status_code)
