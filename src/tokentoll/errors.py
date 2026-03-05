from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse


class TokenTollError(Exception):
    """Base exception for TokenToll."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code


class ChallengeExpiredError(TokenTollError):
    def __init__(self) -> None:
        super().__init__("Challenge has expired", 410)


class ChallengeNotFoundError(TokenTollError):
    def __init__(self) -> None:
        super().__init__("Challenge not found", 404)


class NonceReusedError(TokenTollError):
    def __init__(self) -> None:
        super().__init__("Nonce already used", 409)


class InvalidCommitmentError(TokenTollError):
    def __init__(self) -> None:
        super().__init__("Invalid commitment hash", 400)


class InvalidSiteKeyError(TokenTollError):
    def __init__(self) -> None:
        super().__init__("Invalid or inactive site key", 400)


class RateLimitExceededError(TokenTollError):
    def __init__(self, retry_after: int, remaining: int | None = None) -> None:
        super().__init__("Rate limit exceeded", 429)
        self.retry_after = retry_after
        self.remaining = remaining


logger = logging.getLogger("tokentoll.errors")


async def tokentoll_error_handler(
    request: Request,
    exc: TokenTollError,
) -> JSONResponse:
    headers: dict[str, str] = {}
    if isinstance(exc, RateLimitExceededError):
        headers["Retry-After"] = str(exc.retry_after)
        if exc.remaining is not None:
            headers["X-RateLimit-Remaining"] = str(exc.remaining)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message},
        headers=headers,
    )


async def generic_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.error("Unhandled exception", exc_info=exc, extra={"request_id": request_id})
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )
