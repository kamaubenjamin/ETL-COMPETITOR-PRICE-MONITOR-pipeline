import pytest

from src.ui.streamlit.api_client import APIClientError
from src.ui.streamlit.api_provider import (
    DocumentIntelligenceAPIProvider,
    safe_api_preview_error,
)


class FailingClient:
    def __init__(self, code, raw_message, status_code=None):
        self.error = APIClientError(code, raw_message, status_code=status_code)

    def get(self, path, *, params=None):
        raise self.error


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("api_unavailable", "Document Intelligence API is unavailable."),
        ("runtime_unavailable", "Document Intelligence runtime is unavailable."),
        ("composition_failed", "Document Intelligence runtime is unavailable."),
        ("auth_configuration_error", "API runtime authentication is unavailable."),
        ("provider_configuration_error", "API runtime data provider is unavailable."),
        ("authentication_required", "Authentication is required for this API preview."),
        ("authorization_denied", "This identity is not permitted to view the requested data."),
        ("resource_not_found", "The requested resource is not available in this scope."),
        ("invalid_response", "Document Intelligence API returned an invalid response."),
    ],
)
def test_api_runtime_errors_map_to_fixed_safe_operator_states(code, expected):
    assert safe_api_preview_error(code) == expected
    provider = DocumentIntelligenceAPIProvider(
        FailingClient(code, "C:/private/raw token claim and stack trace")
    )
    assert provider.documents() == []
    assert provider.runtime_state() == {
        "available": False,
        "code": code,
        "message": expected,
    }
    assert "private" not in provider.last_error.lower()
    assert "token" not in provider.last_error.lower()


def test_invalid_base_url_state_is_fixed_and_does_not_reflect_input():
    provider = DocumentIntelligenceAPIProvider(None, initial_error_code="invalid_configuration")
    assert provider.documents() == []
    assert provider.runtime_state()["message"] == "API preview configuration is invalid."


def test_missing_client_is_a_safe_runtime_unavailable_state():
    provider = DocumentIntelligenceAPIProvider(None)
    assert provider.runtime_state() == {
        "available": False,
        "code": "runtime_unavailable",
        "message": "Document Intelligence runtime is unavailable.",
    }
