from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tokentoll.crypto import generate_rsa_key_pair
from tokentoll.models import Challenge, UsedNonce
from tokentoll.routers import challenges as challenges_router
from tokentoll.services import verify_service
from tokentoll.services.site_service import create_site


async def _create_challenge(
    db_session: AsyncSession,
    answer_key: dict[str, str],
    pass_threshold: float = 0.8,
    expires_at: datetime | None = None,
) -> Challenge:
    site, _ = await create_site(db_session, "Test Site")
    expires_at = expires_at or (
        datetime.now(timezone.utc) + timedelta(minutes=5)
    )
    challenge = Challenge(
        site_id=site.id,
        context="{}",
        answer_key=json.dumps(answer_key),
        question_count=len(answer_key),
        pass_threshold=pass_threshold,
        expires_at=expires_at,
        solved=False,
        solved_at=None,
    )
    db_session.add(challenge)
    await db_session.commit()
    await db_session.refresh(challenge)
    return challenge


@pytest.mark.asyncio
async def test_verify_api_happy_path(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    private_key, _ = generate_rsa_key_pair()
    monkeypatch.setattr(
        challenges_router, "load_or_generate_private_key", lambda _: private_key
    )
    challenge = await _create_challenge(
        db_session,
        {"q1": "alpha", "q2": "bravo", "q3": "charlie"},
        pass_threshold=0.6,
    )
    answers = {"q1": "alpha", "q2": "bravo", "q3": "wrong"}
    nonce = "nonce-api"
    commitment = hashlib.sha256(
        (verify_service.canonical_answers(answers) + nonce).encode()
    ).hexdigest()

    response = await client.post(
        "/verify",
        json={
            "challenge_id": str(challenge.id),
            "nonce": nonce,
            "answers": answers,
            "commitment": commitment,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["token"]
    assert payload["score"] == pytest.approx(0.67, abs=0.01)

    refreshed = await db_session.get(Challenge, challenge.id)
    assert refreshed is not None
    assert refreshed.solved is True
    assert refreshed.solved_at is not None

    nonce_result = await db_session.execute(
        select(UsedNonce).where(
            UsedNonce.challenge_id == challenge.id,
            UsedNonce.nonce == nonce,
        )
    )
    assert nonce_result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_verify_api_rejects_invalid_commitment(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    challenge = await _create_challenge(db_session, {"q1": "alpha"})

    response = await client.post(
        "/verify",
        json={
            "challenge_id": str(challenge.id),
            "nonce": "nonce-invalid",
            "answers": {"q1": "alpha"},
            "commitment": "invalid",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"] == "Invalid commitment"


@pytest.mark.asyncio
async def test_verify_api_rejects_reused_nonce(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    challenge = await _create_challenge(db_session, {"q1": "alpha"})
    nonce = "nonce-reused"
    db_session.add(UsedNonce(challenge_id=challenge.id, nonce=nonce))
    await db_session.commit()

    answers = {"q1": "alpha"}
    commitment = hashlib.sha256(
        (verify_service.canonical_answers(answers) + nonce).encode()
    ).hexdigest()

    response = await client.post(
        "/verify",
        json={
            "challenge_id": str(challenge.id),
            "nonce": nonce,
            "answers": answers,
            "commitment": commitment,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"] == "Nonce already used"


@pytest.mark.asyncio
async def test_verify_api_rejects_expired_challenge(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    challenge = await _create_challenge(
        db_session, {"q1": "alpha"}, expires_at=expires_at
    )

    answers = {"q1": "alpha"}
    nonce = "nonce-expired"
    commitment = hashlib.sha256(
        (verify_service.canonical_answers(answers) + nonce).encode()
    ).hexdigest()

    response = await client.post(
        "/verify",
        json={
            "challenge_id": str(challenge.id),
            "nonce": nonce,
            "answers": answers,
            "commitment": commitment,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"] == "Challenge expired"


@pytest.mark.asyncio
async def test_verify_api_rejects_missing_challenge(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/verify",
        json={
            "challenge_id": "3d8d7e4f-53d7-4f42-b0c1-0bcbdf1e64f2",
            "nonce": "nonce-missing",
            "answers": {"q1": "alpha"},
            "commitment": "invalid",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"] == "Challenge not found"
