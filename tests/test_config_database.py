from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from tokentoll.config import get_settings
from tokentoll.database import get_db, get_engine


def test_get_settings_defaults() -> None:
    settings = get_settings()

    assert settings.database_url == "sqlite+aiosqlite:///./tokentoll.db"
    assert settings.secret_key == "dev-secret-change-me"
    assert settings.token_ttl_seconds == 300
    assert settings.challenge_expiry_seconds == 600
    assert settings.rsa_private_key_path is None
    assert settings.debug is False


@pytest.mark.asyncio
async def test_get_engine_returns_async_engine() -> None:
    engine = get_engine("sqlite+aiosqlite:///:memory:")

    assert isinstance(engine, AsyncEngine)
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_db_yields_session() -> None:
    async for session in get_db():
        assert isinstance(session, AsyncSession)
        break
