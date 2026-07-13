from src.ui.streamlit.api_client import APIClientError
from src.ui.streamlit.api_provider import DocumentIntelligenceAPIProvider


class FailingClient:
    def __init__(self, error):
        self.error = error

    def get(self, path, *, params=None):
        raise self.error


def _read_error(code, message, status_code):
    provider = DocumentIntelligenceAPIProvider(
        FailingClient(APIClientError(code, message, status_code=status_code))
    )
    assert provider.documents() == []
    return provider


def test_unauthenticated_preview_uses_fixed_safe_state():
    provider = _read_error("authentication_required", "raw backend identity detail", 401)
    assert provider.last_error_code == "authentication_required"
    assert provider.last_error == "Authentication is required for this API preview."
    assert "raw backend" not in provider.last_error


def test_unauthorized_and_concealed_scope_states_are_safe():
    forbidden = _read_error("authorization_denied", "tenant=private", 403)
    concealed = _read_error("resource_not_found", "document and tenant internals", 404)
    assert forbidden.last_error == "This identity is not permitted to view the requested data."
    assert concealed.last_error == "The requested resource is not available in this scope."
    assert "private" not in forbidden.last_error
    assert "tenant" not in concealed.last_error.lower()


def test_unavailable_and_unknown_errors_do_not_reflect_exception_text():
    unavailable = _read_error("api_unavailable", "C:/private/service failed", None)
    unknown = _read_error("unexpected_backend_code", "stack trace detail", 500)
    assert unavailable.last_error == "Document Intelligence API is unavailable."
    assert unknown.last_error == "Document Intelligence API request could not be completed."
    assert "private" not in unavailable.last_error
    assert "stack" not in unknown.last_error

