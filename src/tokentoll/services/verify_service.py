from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tokentoll.challenges.normalization import normalize_answer
from tokentoll.models import Challenge, Site, UsedNonce
from tokentoll.services.token_service import create_verification_token


def canonical_answers(answers: dict[str, str]) -> str:
    """Canonical JSON serialization of answers for commitment verification."""
    return json.dumps(answers, sort_keys=True, separators=(",", ":"))


def verify_commitment(
    answers: dict[str, str], nonce: str, commitment: str
) -> bool:
    """Verify that commitment == sha256(canonical(answers) + nonce)."""
    expected = hashlib.sha256(
        (canonical_answers(answers) + nonce).encode()
    ).hexdigest()
    return hmac.compare_digest(expected, commitment)


def _normalize_for_format(answer: str, answer_format: str) -> str:
    try:
        return normalize_answer(answer, answer_format)
    except ValueError:
        return answer.strip().lower()


def score_answers(
    submitted: dict[str, str],
    answer_key: dict[str, str],
    answer_formats: dict[str, str],
) -> float:
    """Score submitted answers against the answer key."""
    if not answer_key:
        return 0.0

    correct = 0
    for question_id, expected in answer_key.items():
        submitted_answer = submitted.get(question_id)
        if submitted_answer is None:
            continue

        answer_format = answer_formats.get(question_id, "single_word")
        normalized_expected = _normalize_for_format(expected, answer_format)
        normalized_submitted = _normalize_for_format(
            submitted_answer, answer_format
        )
        if normalized_expected == normalized_submitted:
            correct += 1

    return correct / len(answer_key)


def _parse_answer_key(
    raw_answer_key: dict[str, object],
) -> tuple[dict[str, str], dict[str, str]]:
    answer_key: dict[str, str] = {}
    answer_formats: dict[str, str] = {}
    for question_id, payload in raw_answer_key.items():
        if isinstance(payload, dict):
            answer_value = payload.get("answer")
            if answer_value is not None:
                answer_key[question_id] = str(answer_value)
            format_value = payload.get("format")
            if isinstance(format_value, str):
                answer_formats[question_id] = format_value
        else:
            answer_key[question_id] = str(payload)

    return answer_key, answer_formats


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


async def _record_nonce(
    db: AsyncSession, challenge: Challenge, nonce: str
) -> None:
    db.add(UsedNonce(challenge_id=challenge.id, nonce=nonce))
    await db.commit()


async def verify_challenge(
    db: AsyncSession,
    challenge_id: str,
    nonce: str,
    answers: dict[str, str],
    commitment: str,
    private_key: rsa.RSAPrivateKey,
) -> dict[str, object]:
    """Full verification flow for challenge answers."""
    try:
        challenge_uuid = uuid.UUID(challenge_id)
    except (TypeError, ValueError):
        return {
            "success": False,
            "token": None,
            "score": None,
            "error": "Invalid challenge id",
        }

    result = await db.execute(
        select(Challenge).where(Challenge.id == challenge_uuid)
    )
    challenge = result.scalar_one_or_none()
    if challenge is None:
        return {
            "success": False,
            "token": None,
            "score": None,
            "error": "Challenge not found",
        }

    now = datetime.now(timezone.utc)
    if _normalize_datetime(challenge.expires_at) <= now:
        await _record_nonce(db, challenge, nonce)
        return {
            "success": False,
            "token": None,
            "score": None,
            "error": "Challenge expired",
        }

    nonce_result = await db.execute(
        select(UsedNonce).where(
            UsedNonce.challenge_id == challenge.id, UsedNonce.nonce == nonce
        )
    )
    if nonce_result.scalar_one_or_none() is not None:
        return {
            "success": False,
            "token": None,
            "score": None,
            "error": "Nonce already used",
        }

    if not verify_commitment(answers, nonce, commitment):
        await _record_nonce(db, challenge, nonce)
        return {
            "success": False,
            "token": None,
            "score": None,
            "error": "Invalid commitment",
        }

    raw_answer_key = json.loads(challenge.answer_key)
    answer_key, answer_formats = _parse_answer_key(raw_answer_key)
    score = score_answers(answers, answer_key, answer_formats)

    if score < challenge.pass_threshold:
        await _record_nonce(db, challenge, nonce)
        return {
            "success": False,
            "token": None,
            "score": score,
            "error": "Score below pass threshold",
        }

    site_result = await db.execute(
        select(Site).where(Site.id == challenge.site_id)
    )
    site = site_result.scalar_one_or_none()
    if site is None:
        return {
            "success": False,
            "token": None,
            "score": None,
            "error": "Site not found",
        }

    challenge.solved = True
    challenge.solved_at = now
    db.add(UsedNonce(challenge_id=challenge.id, nonce=nonce))
    await db.commit()

    token = create_verification_token(
        private_key=private_key,
        challenge_id=str(challenge.id),
        site_key=site.site_key,
        ttl_seconds=site.token_ttl_seconds,
    )

    return {
        "success": True,
        "token": token,
        "score": score,
        "error": None,
    }
