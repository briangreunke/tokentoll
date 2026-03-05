from __future__ import annotations

import logging
from time import perf_counter

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


logger = logging.getLogger("tokentoll.middleware.logging")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with structured metadata."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        start_time = perf_counter()
        response = await call_next(request)
        duration_ms = (perf_counter() - start_time) * 1000
        request_id = getattr(request.state, "request_id", None)
        client_ip = request.client.host if request.client else "unknown"
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "request_id": request_id,
                "client_ip": client_ip,
            },
        )
        return response
