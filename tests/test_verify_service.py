from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tokentoll.crypto import generate_rsa_key_pair
from tokentoll.models import Challenge, Site, UsedNonce
from tokentoll.services import verify_service
from tokentoll.services.site_service import create_site
from tokentoll.services.token_service import decode_verification_token


def test_canonical_answers_is_deterministic() -> None:
    answers = {"b": "2", "a": "1"}

    canonical = verify_service.canonical_answers(answers)

    assert canonical == '{"a":"1","b":"2"}'


def test_verify_commitment_matches_expected_hash() -> None:
    answers = {"q1": "alpha", "q2": "2"}
    nonce = "nonce-123"
    canonical = verify_service.canonical_answers(answers)
    commitment = hashlib.sha256((canonical + nonce).encode()).hexdigest()

    assert verify_service.verify_commitment(answers, nonce, commitment) is True
    assert (
        verify_service.verify_commitment(answers, nonce, "wrong") is False
    )


def test_score_answers_uses_normalization_formats() -> None:
    submitted = {
        "q1": "  ALPHA ",
        "q2": "2",
        "q3": "Yes",
        "q4": "b, a",
    }
    answer_key = {
        "q1": "alpha",
        "q2": "2",
        "q3": "true",
        "q4": "a, b",
    }
    answer_formats = {
        "q1": "single_word",
        "q2": "integer",
        "q3": "boolean",
        "q4": "comma_separated_list",
    }

    score = verify_service.score_answers(submitted, answer_key, answer_formats)

    assert score == 1.0


def test_score_answers_handles_partial_correct() -> None:
    submitted = {"q1": "alpha", "q2": "wrong"}
    answer_key = {"q1": "alpha", "q2": "beta"}
    answer_formats = {"q1": "single_word", "q2": "single_word"}

    score = verify_service.score_answers(submitted, answer_key, answer_formats)

    assert score == 0.5


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
async def test_verify_challenge_success_records_nonce_and_token(
    db_session: AsyncSession,
) -> None:
    private_key, public_key = generate_rsa_key_pair()
    answer_key = {
        "q1": "alpha",
        "q2": "2",
        "q3": "true",
        "q4": "cat",
        "q5": "dog",
    }
    challenge = await _create_challenge(db_session, answer_key)
    answers = {
        "q1": " alpha ",
        "q2": "2",
        "q3": "true",
        "q4": "cat",
        "q5": "wrong",
    }
    nonce = "nonce-123"
    commitment = hashlib.sha256(
        (verify_service.canonical_answers(answers) + nonce).encode()
    ).hexdigest()

    result = await verify_service.verify_challenge(
        db=db_session,
        challenge_id=str(challenge.id),
        nonce=nonce,
        answers=answers,
        commitment=commitment,
        private_key=private_key,
    )

    assert result["success"] is True
    assert result["score"] == 0.8
    assert result["token"]

    claims = decode_verification_token(result["token"], public_key)
    assert claims["sub"] == str(challenge.id)
    site_result = await db_session.execute(
        select(Site).where(Site.id == challenge.site_id)
    )
    site = site_result.scalar_one()
    assert claims["site_key"] == site.site_key

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
async def test_verify_challenge_below_threshold_records_nonce(
    db_session: AsyncSession,
) -> None:
    private_key, _ = generate_rsa_key_pair()
    answer_key = {
        "q1": "alpha",
        "q2": "bravo",
        "q3": "charlie",
        "q4": "delta",
        "q5": "echo",
    }
    challenge = await _create_challenge(db_session, answer_key)
    answers = {
        "q1": "alpha",
        "q2": "wrong",
        "q3": "charlie",
        "q4": "wrong",
        "q5": "echo",
    }
    nonce = "nonce-456"
    commitment = hashlib.sha256(
        (verify_service.canonical_answers(answers) + nonce).encode()
    ).hexdigest()

    result = await verify_service.verify_challenge(
        db=db_session,
        challenge_id=str(challenge.id),
        nonce=nonce,
        answers=answers,
        commitment=commitment,
        private_key=private_key,
    )

    assert result["success"] is False
    assert result["score"] == 0.6
    assert result["error"] == "Score below pass threshold"

    refreshed = await db_session.get(Challenge, challenge.id)
    assert refreshed is not None
    assert refreshed.solved is False
    assert refreshed.solved_at is None

    nonce_result = await db_session.execute(
        select(UsedNonce).where(
            UsedNonce.challenge_id == challenge.id,
            UsedNonce.nonce == nonce,
        )
    )
    assert nonce_result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_verify_challenge_rejects_invalid_commitment(
    db_session: AsyncSession,
) -> None:
    private_key, _ = generate_rsa_key_pair()
    answer_key = {"q1": "alpha"}
    challenge = await _create_challenge(db_session, answer_key)
    answers = {"q1": "alpha"}
    nonce = "nonce-789"

    result = await verify_service.verify_challenge(
        db=db_session,
        challenge_id=str(challenge.id),
        nonce=nonce,
        answers=answers,
        commitment="invalid",
        private_key=private_key,
    )

    assert result["success"] is False
    assert result["error"] == "Invalid commitment"

    nonce_result = await db_session.execute(
        select(UsedNonce).where(
            UsedNonce.challenge_id == challenge.id,
            UsedNonce.nonce == nonce,
        )
    )
    assert nonce_result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_verify_challenge_rejects_reused_nonce(
    db_session: AsyncSession,
) -> None:
    private_key, _ = generate_rsa_key_pair()
    answer_key = {"q1": "alpha"}
    challenge = await _create_challenge(db_session, answer_key)
    nonce = "nonce-reused"
    db_session.add(UsedNonce(challenge_id=challenge.id, nonce=nonce))
    await db_session.commit()

    answers = {"q1": "alpha"}
    commitment = hashlib.sha256(
        (verify_service.canonical_answers(answers) + nonce).encode()
    ).hexdigest()

    result = await verify_service.verify_challenge(
        db=db_session,
        challenge_id=str(challenge.id),
        nonce=nonce,
        answers=answers,
        commitment=commitment,
        private_key=private_key,
    )

    assert result["success"] is False
    assert result["error"] == "Nonce already used"

    nonce_result = await db_session.execute(
        select(UsedNonce).where(
            UsedNonce.challenge_id == challenge.id,
            UsedNonce.nonce == nonce,
        )
    )
    assert nonce_result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_verify_challenge_rejects_expired_challenge(
    db_session: AsyncSession,
) -> None:
    private_key, _ = generate_rsa_key_pair()
    answer_key = {"q1": "alpha"}
    expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    challenge = await _create_challenge(
        db_session, answer_key, expires_at=expires_at
    )
    answers = {"q1": "alpha"}
    nonce = "nonce-expired"
    commitment = hashlib.sha256(
        (verify_service.canonical_answers(answers) + nonce).encode()
    ).hexdigest()

    result = await verify_service.verify_challenge(
        db=db_session,
        challenge_id=str(challenge.id),
        nonce=nonce,
        answers=answers,
        commitment=commitment,
        private_key=private_key,
    )

    assert result["success"] is False
    assert result["error"] == "Challenge expired"

    nonce_result = await db_session.execute(
        select(UsedNonce).where(
            UsedNonce.challenge_id == challenge.id,
            UsedNonce.nonce == nonce,
        )
    )
    assert nonce_result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_verify_challenge_rejects_missing_challenge(
    db_session: AsyncSession,
) -> None:
    private_key, _ = generate_rsa_key_pair()

    result = await verify_service.verify_challenge(
        db=db_session,
        challenge_id="3d8d7e4f-53d7-4f42-b0c1-0bcbdf1e64f2",
        nonce="nonce",
        answers={"q1": "alpha"},
        commitment="invalid",
        private_key=private_key,
    )

    assert result["success"] is False
    assert result["error"] == "Challenge not found"
