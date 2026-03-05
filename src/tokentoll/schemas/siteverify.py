from __future__ import annotations

from pydantic import BaseModel


class SiteverifyRequest(BaseModel):
    secret_key: str
    token: str


class SiteverifyResponse(BaseModel):
    success: bool
    challenge_id: str | None = None
    site_key: str | None = None
    solved_at: str | None = None
    error: str | None = None
