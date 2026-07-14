import json

from src.platform_runtime import RuntimeValidationError, validate_runtime_config


def test_runtime_error_uses_fixed_safe_message_and_allowlisted_field():
    secret = "token=super-secret C:/private/state.sqlite3"
    error = RuntimeValidationError("not-a-code", field=secret)
    payload = json.dumps(error.to_dict())
    assert error.code.value == "invalid_config"
    assert error.field is None
    assert secret not in payload
    assert "super-secret" not in str(error)
    assert "private" not in str(error)


def test_validation_of_non_config_does_not_reflect_raw_input():
    raw = {"password": "private-value", "traceback": "stack detail"}
    payload = json.dumps(validate_runtime_config(raw).to_dict())
    assert "private-value" not in payload
    assert "stack detail" not in payload
    assert "invalid_config" in payload

