from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tokentoll.crypto import generate_rsa_key_pair
from tokentoll.models import Challenge
from tokentoll.services.site_service import create_site
from tokentoll.services.token_service import (
    create_verification_token,
    decode_verification_token,
    siteverify,
)


def test_create_and_decode_verification_token_round_trip() -> None:
    private_key, public_key = generate_rsa_key_pair()
    challenge_id = str(uuid.uuid4())
    site_key = "site-key"

    token = create_verification_token(
        private_key=private_key,
        challenge_id=challenge_id,
        site_key=site_key,
        ttl_seconds=120,
    )
    claims = decode_verification_token(token, public_key)

    assert claims["sub"] == challenge_id
    assert claims["site_key"] == site_key
    assert isinstance(claims["iat"], int)
    assert isinstance(claims["exp"], int)
    assert claims["exp"] - claims["iat"] == 120
    assert isinstance(claims["jti"], str)
    assert claims["jti"]


def test_decode_verification_token_raises_on_expired_token() -> None:
    private_key, public_key = generate_rsa_key_pair()
    token = create_verification_token(
        private_key=private_key,
        challenge_id=str(uuid.uuid4()),
        site_key="site-key",
        ttl_seconds=-1,
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_verification_token(token, public_key)


def test_decode_verification_token_raises_on_wrong_key() -> None:
    private_key, _ = generate_rsa_key_pair()
    _, other_public_key = generate_rsa_key_pair()

    token = create_verification_token(
        private_key=private_key,
        challenge_id=str(uuid.uuid4()),
        site_key="site-key",
    )

    with pytest.raises(jwt.InvalidSignatureError):
        decode_verification_token(token, other_public_key)


@pytest.mark.asyncio
async def test_siteverify_success(db_session: AsyncSession) -> None:
    private_key, public_key = generate_rsa_key_pair()
    site, raw_secret = await create_site(db_session, "Site One")

    solved_at = datetime.now(timezone.utc).replace(microsecond=0)
    challenge = Challenge(
        site_id=site.id,
        context="{}",
        answer_key="{}",
        question_count=1,
        expires_at=solved_at + timedelta(minutes=5),
        solved=True,
        solved_at=solved_at,
    )
    db_session.add(challenge)
    await db_session.commit()
    await db_session.refresh(challenge)

    token = create_verification_token(
        private_key=private_key,
        challenge_id=str(challenge.id),
        site_key=site.site_key,
    )

    response = await siteverify(db_session, raw_secret, token, public_key)

    assert response["success"] is True
    assert response["challenge_id"] == str(challenge.id)
    assert response["site_key"] == site.site_key
    assert response["solved_at"] == solved_at.isoformat()


@pytest.mark.asyncio
async def test_siteverify_rejects_invalid_secret(db_session: AsyncSession) -> None:
    private_key, public_key = generate_rsa_key_pair()
    site, _ = await create_site(db_session, "Site One")

    token = create_verification_token(
        private_key=private_key,
        challenge_id=str(uuid.uuid4()),
        site_key=site.site_key,
    )

    response = await siteverify(db_session, "wrong-secret", token, public_key)

    assert response == {"success": False, "error": "invalid_secret"}


@pytest.mark.asyncio
async def test_siteverify_rejects_site_key_mismatch(
    db_session: AsyncSession,
) -> None:
    private_key, public_key = generate_rsa_key_pair()
    site_one, _ = await create_site(db_session, "Site One")
    _, site_two_secret = await create_site(db_session, "Site Two")

    token = create_verification_token(
        private_key=private_key,
        challenge_id=str(uuid.uuid4()),
        site_key=site_one.site_key,
    )

    response = await siteverify(db_session, site_two_secret, token, public_key)

    assert response == {"success": False, "error": "site_key_mismatch"}


@pytest.mark.asyncio
async def test_siteverify_rejects_expired_token(db_session: AsyncSession) -> None:
    private_key, public_key = generate_rsa_key_pair()
    site, raw_secret = await create_site(db_session, "Site One")

    token = create_verification_token(
        private_key=private_key,
        challenge_id=str(uuid.uuid4()),
        site_key=site.site_key,
        ttl_seconds=-1,
    )

    response = await siteverify(db_session, raw_secret, token, public_key)

    assert response == {"success": False, "error": "token_expired"}


@pytest.mark.asyncio
async def test_siteverify_rejects_missing_challenge(
    db_session: AsyncSession,
) -> None:
    private_key, public_key = generate_rsa_key_pair()
    site, raw_secret = await create_site(db_session, "Site One")

    token = create_verification_token(
        private_key=private_key,
        challenge_id=str(uuid.uuid4()),
        site_key=site.site_key,
    )

    response = await siteverify(db_session, raw_secret, token, public_key)

    assert response == {"success": False, "error": "challenge_not_found"}


@pytest.mark.asyncio
async def test_siteverify_rejects_unsolved_challenge(
    db_session: AsyncSession,
) -> None:
    private_key, public_key = generate_rsa_key_pair()
    site, raw_secret = await create_site(db_session, "Site One")

    challenge = Challenge(
        site_id=site.id,
        context="{}",
        answer_key="{}",
        question_count=1,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        solved=False,
        solved_at=None,
    )
    db_session.add(challenge)
    await db_session.commit()
    await db_session.refresh(challenge)

    token = create_verification_token(
        private_key=private_key,
        challenge_id=str(challenge.id),
        site_key=site.site_key,
    )

    response = await siteverify(db_session, raw_secret, token, public_key)

    assert response == {"success": False, "error": "challenge_not_solved"}
