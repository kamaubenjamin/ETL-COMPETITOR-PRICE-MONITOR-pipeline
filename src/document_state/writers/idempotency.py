"""Deterministic, non-disclosing idempotency keys for writer commands."""

from __future__ import annotations

from enum import Enum
import hashlib
import json
from typing import Any

from ..privacy import bounded_string
from .errors import DocumentStateWriterError


MAX_IDEMPOTENCY_KEY_LENGTH = 96


class IdempotencyDomain(str, Enum):
    DOCUMENT = "document"
    LIFECYCLE = "lifecycle"
    PROCESSING = "processing"
    VALIDATION = "validation"
    MATCHING = "matching"
    REVIEW = "review"
    CORRECTION = "correction"
    REPROCESS = "reprocess"
    WORKFLOW = "workflow"
    AUDIT = "audit"


def _part(value: Any) -> str | int | bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if abs(value) > 9_007_199_254_740_991:
            raise ValueError
        return value
    if isinstance(value, str):
        return bounded_string(value, "idempotency part", maximum=256)
    raise ValueError


def make_idempotency_key(domain: IdempotencyDomain | str, *parts: str | int | bool) -> str:
    try:
        safe_domain = domain.value if isinstance(domain, IdempotencyDomain) else IdempotencyDomain(domain).value
        normalized = [_part(item) for item in parts]
        if not normalized:
            raise ValueError
    except (TypeError, ValueError) as exc:
        raise DocumentStateWriterError("invalid_idempotency_key", field="idempotency_key") from exc
    canonical = json.dumps(normalized, ensure_ascii=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    key = f"dsw:{safe_domain}:{digest}"
    if len(key) > MAX_IDEMPOTENCY_KEY_LENGTH:
        raise DocumentStateWriterError("invalid_idempotency_key", field="idempotency_key")
    return key
