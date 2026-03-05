from __future__ import annotations

from collections.abc import AsyncGenerator
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tokentoll.database import get_db
from tokentoll.main import create_app
from tokentoll.models import Challenge
from tokentoll.models.base import Base
import tokentoll.models  # noqa: F401


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


@pytest.fixture
async def registered_site(client: AsyncClient) -> tuple[str, str]:
    response = await client.post("/sites/", json={"name": "Integration Test"})
    assert response.status_code == 201
    payload = response.json()
    return payload["site_key"], payload["secret_key"]


@pytest.fixture
async def challenge_with_answers(
    client: AsyncClient,
    registered_site: tuple[str, str],
    db_session: AsyncSession,
) -> tuple[str, dict[str, str], dict[str, str]]:
    site_key, _ = registered_site
    response = await client.post("/challenge", json={"site_key": site_key})
    assert response.status_code == 201
    payload = response.json()
    challenge_id = payload["challenge_id"]
    answer_formats = {
        question["id"]: question["answer_format"]
        for question in payload["questions"]
    }

    challenge = await db_session.get(Challenge, uuid.UUID(challenge_id))
    assert challenge is not None
    answer_key = json.loads(challenge.answer_key)
    answers = {question_id: str(answer) for question_id, answer in answer_key.items()}
    return challenge_id, answers, answer_formats
