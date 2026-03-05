from __future__ import annotations

from collections.abc import AsyncGenerator
import json
import uuid

import httpx
from httpx import ASGITransport
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tokentoll.client.client import TokenTollClient
from tokentoll.database import get_db
from tokentoll.main import create_app
from tokentoll.models import Challenge


def _answers_from_challenge(challenge: Challenge) -> dict[str, str]:
    raw_answer_key = json.loads(challenge.answer_key)
    answers: dict[str, str] = {}
    for question_id, payload in raw_answer_key.items():
        if isinstance(payload, dict):
            answer_value = payload.get("answer")
            if answer_value is not None:
                answers[question_id] = str(answer_value)
        else:
            answers[question_id] = str(payload)
    return answers


@pytest.fixture
async def sdk_app(db_session: AsyncSession) -> AsyncGenerator[object, None]:
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
async def sdk_client(
    sdk_app: object, registered_site: tuple[str, str]
) -> AsyncGenerator[TokenTollClient, None]:
    site_key, _ = registered_site
    transport = ASGITransport(app=sdk_app)
    client = TokenTollClient(
        base_url="http://test",
        site_key=site_key,
        transport=transport,
    )
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_get_challenge_returns_challenge(
    sdk_client: TokenTollClient,
) -> None:
    challenge = await sdk_client.get_challenge()

    assert challenge.challenge_id
    assert challenge.context
    assert challenge.questions
    assert challenge.expires_at


@pytest.mark.asyncio
async def test_submit_answers_returns_verification_result(
    sdk_client: TokenTollClient,
    db_session: AsyncSession,
) -> None:
    challenge = await sdk_client.get_challenge()
    challenge_row = await db_session.get(
        Challenge, uuid.UUID(challenge.challenge_id)
    )
    assert challenge_row is not None

    answers = _answers_from_challenge(challenge_row)
    result = await sdk_client.submit_answers(challenge.challenge_id, answers)

    assert result.success is True
    assert result.token
    assert result.score is not None
    assert result.error is None


@pytest.mark.asyncio
async def test_get_challenge_raises_for_invalid_site_key(
    sdk_app: object,
) -> None:
    transport = ASGITransport(app=sdk_app)
    client = TokenTollClient(
        base_url="http://test",
        site_key="invalid-site-key",
        transport=transport,
    )

    with pytest.raises(httpx.HTTPStatusError):
        await client.get_challenge()

    await client.close()


@pytest.mark.asyncio
async def test_async_context_manager_supports_request(
    sdk_app: object, registered_site: tuple[str, str]
) -> None:
    site_key, _ = registered_site
    transport = ASGITransport(app=sdk_app)

    async with TokenTollClient(
        base_url="http://test",
        site_key=site_key,
        transport=transport,
    ) as client:
        challenge = await client.get_challenge()

    assert challenge.challenge_id


@pytest.mark.asyncio
async def test_can_use_provided_http_client(
    sdk_app: object, registered_site: tuple[str, str]
) -> None:
    site_key, _ = registered_site
    transport = ASGITransport(app=sdk_app)

    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as http_client:
        client = TokenTollClient(
            base_url="http://test",
            site_key=site_key,
            http_client=http_client,
        )

        challenge = await client.get_challenge()
        assert challenge.challenge_id

        await client.close()
        assert http_client.is_closed is False
