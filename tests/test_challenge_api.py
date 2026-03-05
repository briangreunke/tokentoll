from __future__ import annotations

import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tokentoll.challenges.types import GeneratedChallenge, Question
from tokentoll.models import Challenge
from tokentoll.services import challenge_service
from tokentoll.services.site_service import create_site


@pytest.mark.asyncio
async def test_request_challenge_returns_public_payload(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    site, _ = await create_site(db_session, "API Site")
    generated = GeneratedChallenge(
        seed="seed",
        puzzle_type="logic",
        context="API context",
        questions=[
            Question(
                id="q1",
                text="Question one?",
                expected_answer="alpha",
                answer_format="single_word",
            )
        ],
        estimated_tokens=11,
    )

    monkeypatch.setattr(
        challenge_service, "generate_challenge", lambda: generated
    )

    response = await client.post("/challenge", json={"site_key": site.site_key})

    assert response.status_code == 201
    payload = response.json()

    assert payload["challenge_id"]
    assert payload["context"] == generated.context
    assert payload["expires_at"]
    assert "answer_key" not in payload
    assert payload["questions"] == [
        {
            "id": "q1",
            "text": "Question one?",
            "answer_format": "single_word",
        }
    ]
    assert "expected_answer" not in payload["questions"][0]

    challenge_id = uuid.UUID(payload["challenge_id"])
    result = await db_session.execute(
        select(Challenge).where(Challenge.id == challenge_id)
    )
    persisted = result.scalar_one()
    assert persisted.context == generated.context
    assert persisted.ip_address is not None
    assert json.loads(persisted.answer_key) == {"q1": "alpha"}


@pytest.mark.asyncio
async def test_request_challenge_invalid_site_key_returns_400(
    client: AsyncClient,
) -> None:
    response = await client.post("/challenge", json={"site_key": "invalid"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or inactive site_key"
