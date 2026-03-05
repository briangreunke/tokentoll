from __future__ import annotations

import hashlib
import re

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tokentoll.models import Site


URLSAFE_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@pytest.mark.asyncio
async def test_register_site_returns_site_and_secret(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    response = await client.post("/sites/", json={"name": "Test"})

    assert response.status_code == 201
    payload = response.json()

    assert payload["id"]
    assert payload["name"] == "Test"
    assert payload["token_ttl_seconds"] == 300
    assert len(payload["site_key"]) >= 32
    assert URLSAFE_PATTERN.match(payload["site_key"])
    assert len(payload["secret_key"]) >= 48
    assert URLSAFE_PATTERN.match(payload["secret_key"])

    expected_hash = hashlib.sha256(payload["secret_key"].encode()).hexdigest()
    result = await db_session.execute(
        select(Site).where(Site.site_key == payload["site_key"])
    )
    persisted = result.scalar_one()
    assert persisted.secret_key_hash == expected_hash


@pytest.mark.asyncio
async def test_register_site_empty_name_returns_422(
    client: AsyncClient,
) -> None:
    response = await client.post("/sites/", json={"name": ""})

    assert response.status_code == 422
