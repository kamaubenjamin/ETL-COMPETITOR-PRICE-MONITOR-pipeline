"""Domain-separated canonical payload fingerprints."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .contracts import json_value


PAYLOAD_FINGERPRINT_DOMAIN = "idp.export.payload.v1"


def canonical_payload_json(payload: Any) -> str:
    from .payloads import ExportPayload

    if not isinstance(payload, ExportPayload):
        raise ValueError("payload must be an ExportPayload")
    try:
        projected = json_value(payload)
        return json.dumps(
            [PAYLOAD_FINGERPRINT_DOMAIN, projected],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError):
        raise ValueError("payload cannot be fingerprinted safely") from None


def fingerprint_export_payload(payload: Any) -> str:
    canonical = canonical_payload_json(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

