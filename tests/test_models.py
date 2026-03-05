from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from tokentoll.models import Challenge, Site, UsedNonce


@pytest.mark.asyncio
async def test_site_defaults_and_persistence(db_session) -> None:
    site = Site(
        name="Example Site",
        site_key="public-key",
        secret_key_hash="secret-hash",
    )

    db_session.add(site)
    await db_session.commit()
    await db_session.refresh(site)

    assert isinstance(site.id, uuid.UUID)
    assert site.token_ttl_seconds == 300
    assert site.is_active is True
    assert site.challenge_rate_limit == 60
    assert site.created_at is not None
    assert site.updated_at is not None


@pytest.mark.asyncio
async def test_challenge_defaults_and_nullable_fields(db_session) -> None:
    site = Site(
        name="Example Site",
        site_key="public-key",
        secret_key_hash="secret-hash",
    )
    db_session.add(site)
    await db_session.flush()

    expires_at = datetime.now(tz=timezone.utc) + timedelta(minutes=5)
    challenge = Challenge(
        site_id=site.id,
        context="{\"q\": \"context\"}",
        answer_key="{\"q1\": \"a1\"}",
        question_count=2,
        expires_at=expires_at,
    )

    db_session.add(challenge)
    await db_session.commit()
    await db_session.refresh(challenge)

    assert isinstance(challenge.id, uuid.UUID)
    assert challenge.pass_threshold == 0.8
    assert challenge.solved is False
    assert challenge.solved_at is None
    assert challenge.ip_address is None
    assert challenge.created_at is not None
    assert challenge.updated_at is not None


@pytest.mark.asyncio
async def test_used_nonce_enforces_unique_constraint(db_session) -> None:
    site = Site(
        name="Example Site",
        site_key="public-key",
        secret_key_hash="secret-hash",
    )
    db_session.add(site)
    await db_session.flush()

    challenge = Challenge(
        site_id=site.id,
        context="{\"q\": \"context\"}",
        answer_key="{\"q1\": \"a1\"}",
        question_count=1,
        expires_at=datetime.now(tz=timezone.utc) + timedelta(minutes=5),
    )
    db_session.add(challenge)
    await db_session.flush()

    first_nonce = UsedNonce(challenge_id=challenge.id, nonce="dup")
    duplicate_nonce = UsedNonce(challenge_id=challenge.id, nonce="dup")

    db_session.add(first_nonce)
    await db_session.commit()

    db_session.add(duplicate_nonce)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
