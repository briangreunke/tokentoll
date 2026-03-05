from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from starlette.datastructures import Headers
from starlette.requests import Request


class RequestIdMiddleware:
    """Add X-Request-ID header to all requests/responses."""

    header_name = "X-Request-ID"

    def __init__(self, app: Callable[[dict, Callable, Callable], Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = headers.get(self.header_name)
        if not request_id:
            request_id = str(uuid.uuid4())

        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id
        request = Request(scope)
        request.state.request_id = request_id

        async def send_wrapper(message) -> None:
            if message["type"] == "http.response.start":
                response_headers = list(message.get("headers", []))
                response_headers.append(
                    (self.header_name.lower().encode(), request_id.encode())
                )
                message["headers"] = response_headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
