from __future__ import annotations

from pydantic import BaseModel, Field


class SiteCreate(BaseModel):
    name: str = Field(min_length=1)


class SiteCreated(BaseModel):
    id: str
    name: str
    site_key: str
    secret_key: str
    token_ttl_seconds: int


class SiteInfo(BaseModel):
    id: str
    name: str
    site_key: str
    is_active: bool
    token_ttl_seconds: int
    created_at: str
