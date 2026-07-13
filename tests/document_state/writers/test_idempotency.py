import pytest

from src.document_state.writers.errors import DocumentStateWriterError
from src.document_state.writers.idempotency import MAX_IDEMPOTENCY_KEY_LENGTH, IdempotencyDomain, make_idempotency_key


def test_idempotency_keys_are_domain_separated_stable_and_bounded():
    first = make_idempotency_key(IdempotencyDomain.LIFECYCLE, "doc-001", "source-001", "received")
    second = make_idempotency_key("lifecycle", "doc-001", "source-001", "received")
    different_domain = make_idempotency_key("audit", "doc-001", "source-001", "received")

    assert first == second
    assert first != different_domain
    assert first.startswith("dsw:lifecycle:")
    assert len(first) <= MAX_IDEMPOTENCY_KEY_LENGTH


def test_idempotency_keys_do_not_disclose_input_values():
    key = make_idempotency_key("correction", "review-001", "private-source-value", 3)
    assert "review-001" not in key
    assert "private-source-value" not in key


@pytest.mark.parametrize("domain,parts", [("unknown", ("a",)), ("audit", ()), ("audit", ({"raw": "payload"},))])
def test_invalid_idempotency_inputs_fail_safely(domain, parts):
    with pytest.raises(DocumentStateWriterError) as raised:
        make_idempotency_key(domain, *parts)
    assert raised.value.code == "invalid_idempotency_key"
    assert "payload" not in str(raised.value)
