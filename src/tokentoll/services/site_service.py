from __future__ import annotations

import hashlib
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tokentoll.models import Site


async def create_site(db: AsyncSession, name: str) -> tuple[Site, str]:
    """Create a site and return (site, raw_secret_key)."""
    site_key = secrets.token_urlsafe(32)
    raw_secret = secrets.token_urlsafe(48)
    secret_hash = hashlib.sha256(raw_secret.encode()).hexdigest()

    site = Site(name=name, site_key=site_key, secret_key_hash=secret_hash)
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return site, raw_secret


async def get_site_by_key(db: AsyncSession, site_key: str) -> Site | None:
    """Look up a site by its public site_key."""
    result = await db.execute(select(Site).where(Site.site_key == site_key))
    return result.scalar_one_or_none()


async def verify_secret_key(db: AsyncSession, secret_key: str) -> Site | None:
    """Verify a raw secret key against stored hashes."""
    secret_hash = hashlib.sha256(secret_key.encode()).hexdigest()
    result = await db.execute(
        select(Site).where(Site.secret_key_hash == secret_hash)
    )
    return result.scalar_one_or_none()
