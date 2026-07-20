"""Dependency-free ASGI request helper for serverless boundary tests."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ASGIResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body)


def asgi_request(
    application,
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: object | None = None,
) -> ASGIResponse:
    encoded_body = b"" if json_body is None else json.dumps(json_body).encode("utf-8")
    request_headers = dict(headers or {})
    if json_body is not None:
        request_headers.setdefault("content-type", "application/json")

    async def invoke() -> ASGIResponse:
        messages: list[dict[str, Any]] = []
        request_sent = False

        async def receive() -> dict[str, Any]:
            nonlocal request_sent
            if request_sent:
                return {"type": "http.disconnect"}
            request_sent = True
            return {"type": "http.request", "body": encoded_body, "more_body": False}

        async def send(message: dict[str, Any]) -> None:
            messages.append(message)

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method.upper(),
            "scheme": "https",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "root_path": "",
            "headers": [
                (name.lower().encode("ascii"), value.encode("ascii"))
                for name, value in request_headers.items()
            ],
            "client": ("127.0.0.1", 43210),
            "server": ("testserver", 443),
        }
        await application(scope, receive, send)
        start = next(message for message in messages if message["type"] == "http.response.start")
        body = b"".join(
            message.get("body", b"")
            for message in messages
            if message["type"] == "http.response.body"
        )
        response_headers = {
            name.decode("latin-1").lower(): value.decode("latin-1")
            for name, value in start.get("headers", [])
        }
        return ASGIResponse(start["status"], response_headers, body)

    return asyncio.run(invoke())
