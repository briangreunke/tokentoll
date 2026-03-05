from __future__ import annotations

import hashlib
import re

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tokentoll.models import Site
from tokentoll.services.site_service import (
    create_site,
    get_site_by_key,
    verify_secret_key,
)


URLSAFE_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@pytest.mark.asyncio
async def test_create_site_generates_keys_and_hashes_secret(
    db_session: AsyncSession,
) -> None:
    site, raw_secret = await create_site(db_session, "Test Site")

    assert site.id is not None
    assert site.name == "Test Site"
    assert len(site.site_key) >= 32
    assert URLSAFE_PATTERN.match(site.site_key)
    assert len(raw_secret) >= 48
    assert URLSAFE_PATTERN.match(raw_secret)

    expected_hash = hashlib.sha256(raw_secret.encode()).hexdigest()
    assert site.secret_key_hash == expected_hash
    assert raw_secret != site.secret_key_hash

    result = await db_session.execute(select(Site).where(Site.id == site.id))
    persisted = result.scalar_one()
    assert persisted.secret_key_hash == expected_hash


@pytest.mark.asyncio
async def test_create_site_generates_unique_site_keys(
    db_session: AsyncSession,
) -> None:
    site_one, secret_one = await create_site(db_session, "Site One")
    site_two, secret_two = await create_site(db_session, "Site Two")

    assert site_one.site_key != site_two.site_key
    assert secret_one != secret_two


@pytest.mark.asyncio
async def test_get_site_by_key_returns_site_or_none(
    db_session: AsyncSession,
) -> None:
    site, _ = await create_site(db_session, "Lookup Site")

    found = await get_site_by_key(db_session, site.site_key)
    missing = await get_site_by_key(db_session, "missing-key")

    assert found is not None
    assert found.id == site.id
    assert missing is None


@pytest.mark.asyncio
async def test_verify_secret_key_returns_site_or_none(
    db_session: AsyncSession,
) -> None:
    site, raw_secret = await create_site(db_session, "Secret Site")

    found = await verify_secret_key(db_session, raw_secret)
    missing = await verify_secret_key(db_session, "invalid-secret")

    assert found is not None
    assert found.id == site.id
    assert missing is None
