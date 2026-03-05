from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tokentoll.challenges.types import GeneratedChallenge, Question
from tokentoll.config import get_settings
from tokentoll.models import Challenge
from tokentoll.services import challenge_service
from tokentoll.services.site_service import create_site


@pytest.mark.asyncio
async def test_create_challenge_persists_answer_key_and_expiry(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    site, _ = await create_site(db_session, "Test Site")
    generated = GeneratedChallenge(
        seed="seed",
        puzzle_type="logic",
        context="Context goes here",
        questions=[
            Question(
                id="q1",
                text="Question one?",
                expected_answer="alpha",
                answer_format="single_word",
            ),
            Question(
                id="q2",
                text="Question two?",
                expected_answer="2",
                answer_format="integer",
            ),
        ],
        estimated_tokens=123,
    )

    def fake_generate_challenge() -> GeneratedChallenge:
        return generated

    monkeypatch.setattr(
        challenge_service, "generate_challenge", fake_generate_challenge
    )

    started_at = datetime.now(timezone.utc)
    challenge, returned = await challenge_service.create_challenge(
        db_session, site.site_key, ip_address="127.0.0.1"
    )
    finished_at = datetime.now(timezone.utc)

    assert returned == generated
    assert challenge.site_id == site.id
    assert challenge.context == generated.context
    assert challenge.question_count == len(generated.questions)
    assert challenge.ip_address == "127.0.0.1"

    stored = json.loads(challenge.answer_key)
    assert stored == {"q1": "alpha", "q2": "2"}

    expiry_seconds = get_settings().challenge_expiry_seconds
    expected_min = started_at + timedelta(seconds=expiry_seconds)
    expected_max = finished_at + timedelta(seconds=expiry_seconds)
    expires_at = challenge.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    assert expected_min <= expires_at <= expected_max

    result = await db_session.execute(
        select(Challenge).where(Challenge.id == challenge.id)
    )
    persisted = result.scalar_one()
    assert persisted.answer_key == challenge.answer_key


@pytest.mark.asyncio
async def test_create_challenge_invalid_site_key_raises(
    db_session: AsyncSession,
) -> None:
    with pytest.raises(ValueError, match="Invalid or inactive site_key"):
        await challenge_service.create_challenge(db_session, "missing-key")


@pytest.mark.asyncio
async def test_create_challenge_inactive_site_raises(
    db_session: AsyncSession,
) -> None:
    site, _ = await create_site(db_session, "Inactive Site")
    site.is_active = False
    await db_session.commit()

    with pytest.raises(ValueError, match="Invalid or inactive site_key"):
        await challenge_service.create_challenge(db_session, site.site_key)
