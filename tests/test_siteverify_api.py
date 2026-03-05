from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tokentoll.crypto import generate_rsa_key_pair
from tokentoll.models import Challenge
from tokentoll.routers import siteverify as siteverify_router
from tokentoll.services.site_service import create_site
from tokentoll.services.token_service import create_verification_token


async def _create_solved_challenge(
    db_session: AsyncSession, site_id: uuid.UUID
) -> Challenge:
    solved_at = datetime.now(timezone.utc).replace(microsecond=0)
    challenge = Challenge(
        site_id=site_id,
        context="{}",
        answer_key="{}",
        question_count=1,
        pass_threshold=0.8,
        expires_at=solved_at + timedelta(minutes=5),
        solved=True,
        solved_at=solved_at,
    )
    db_session.add(challenge)
    await db_session.commit()
    await db_session.refresh(challenge)
    return challenge


@pytest.mark.asyncio
async def test_siteverify_api_happy_path(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_key, public_key = generate_rsa_key_pair()
    monkeypatch.setattr(
        siteverify_router, "get_public_key", lambda: public_key
    )
    site, raw_secret = await create_site(db_session, "Site One")
    challenge = await _create_solved_challenge(db_session, site.id)

    token = create_verification_token(
        private_key=private_key,
        challenge_id=str(challenge.id),
        site_key=site.site_key,
    )

    response = await client.post(
        "/siteverify",
        json={"secret_key": raw_secret, "token": token},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["challenge_id"] == str(challenge.id)
    assert payload["site_key"] == site.site_key
    assert payload["solved_at"] == challenge.solved_at.isoformat()
    assert payload["error"] is None


@pytest.mark.asyncio
async def test_siteverify_api_rejects_invalid_secret(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_key, public_key = generate_rsa_key_pair()
    monkeypatch.setattr(
        siteverify_router, "get_public_key", lambda: public_key
    )
    site, _ = await create_site(db_session, "Site One")

    token = create_verification_token(
        private_key=private_key,
        challenge_id=str(uuid.uuid4()),
        site_key=site.site_key,
    )

    response = await client.post(
        "/siteverify",
        json={"secret_key": "invalid", "token": token},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"] == "invalid_secret"


@pytest.mark.asyncio
async def test_siteverify_api_rejects_expired_token(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_key, public_key = generate_rsa_key_pair()
    monkeypatch.setattr(
        siteverify_router, "get_public_key", lambda: public_key
    )
    site, raw_secret = await create_site(db_session, "Site One")

    token = create_verification_token(
        private_key=private_key,
        challenge_id=str(site.id),
        site_key=site.site_key,
        ttl_seconds=-1,
    )

    response = await client.post(
        "/siteverify",
        json={"secret_key": raw_secret, "token": token},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"] == "token_expired"


@pytest.mark.asyncio
async def test_siteverify_api_rejects_wrong_site_token(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_key, public_key = generate_rsa_key_pair()
    monkeypatch.setattr(
        siteverify_router, "get_public_key", lambda: public_key
    )
    site_one, _ = await create_site(db_session, "Site One")
    site_two, site_two_secret = await create_site(db_session, "Site Two")
    challenge = await _create_solved_challenge(db_session, site_one.id)

    token = create_verification_token(
        private_key=private_key,
        challenge_id=str(challenge.id),
        site_key=site_one.site_key,
    )

    response = await client.post(
        "/siteverify",
        json={"secret_key": site_two_secret, "token": token},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"] == "site_key_mismatch"
    assert payload["site_key"] != site_two.site_key


@pytest.mark.asyncio
async def test_siteverify_api_rejects_malformed_token(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, public_key = generate_rsa_key_pair()
    monkeypatch.setattr(
        siteverify_router, "get_public_key", lambda: public_key
    )
    _, raw_secret = await create_site(db_session, "Site One")

    response = await client.post(
        "/siteverify",
        json={"secret_key": raw_secret, "token": "not-a-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"] == "invalid_token"
