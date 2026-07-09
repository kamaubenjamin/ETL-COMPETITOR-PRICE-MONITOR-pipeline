import json

from src.observability.contracts import RuntimeEvent, RuntimeTraceContext
from src.observability.privacy import (
    REDACTED,
    is_sensitive_key,
    sanitize_attributes,
    sanitize_dimensions,
    sanitize_error_message,
    sanitize_value,
)


def test_sensitive_keys_are_detected():
    assert is_sensitive_key("api_key")
    assert is_sensitive_key("customer_name")
    assert is_sensitive_key("raw_document")
    assert not is_sensitive_key("stage_name")


def test_sanitize_attributes_uses_allowlist_and_drops_sensitive_values():
    attributes = sanitize_attributes(
        {
            "stage_name": "extract",
            "entity_type": "customer",
            "customer_name": "Jane Customer",
            "document_text": "raw text",
            "unexpected": "value",
            "error_code": "E_TEST",
        }
    )

    assert attributes == {
        "stage_name": "extract",
        "entity_type": "customer",
        "error_code": "E_TEST",
    }


def test_sanitize_dimensions_keeps_only_allowed_dimensions():
    dimensions = sanitize_dimensions(
        {
            "runtime": "workflow",
            "status": "succeeded",
            "customer_name": "Jane Customer",
            "unexpected": "value",
        }
    )

    assert dimensions == {
        "runtime": "workflow",
        "status": "succeeded",
    }


def test_sanitize_error_message_redacts_secret_patterns():
    message = sanitize_error_message(
        "request failed api_key=secret123 authorization=Bearer token123"
    )

    assert "secret123" not in message
    assert "token123" not in message
    assert REDACTED in message


def test_sanitize_value_returns_json_compatible_values():
    value = sanitize_value(
        {
            "safe": ["ok", 1, True],
            "token": "secret",
            "nested": {"password": "secret", "status": "failed"},
        }
    )

    assert value == {"safe": ["ok", 1, True], "nested": {"status": "failed"}}
    json.dumps(value)


def test_runtime_event_serialization_excludes_raw_payload_fields():
    trace = RuntimeTraceContext.new_root(
        correlation_id="corr-1",
        trace_id="trace-1",
        span_id="span-1",
    )
    event = RuntimeEvent(
        event_type="entity.write.failed",
        runtime="entity",
        operation="entity.write",
        status="failed",
        severity="error",
        trace=trace,
        attributes={
            "entity_type": "supplier",
            "supplier_name": "Private Supplier",
            "price": "100.00",
            "raw_entity": {"name": "Private Supplier"},
            "error_code": "E_ENTITY_WRITE",
        },
    )

    payload = event.to_dict()
    serialized = json.dumps(payload)

    assert payload["attributes"] == {
        "entity_type": "supplier",
        "error_code": "E_ENTITY_WRITE",
    }
    assert "Private Supplier" not in serialized
    assert "100.00" not in serialized
