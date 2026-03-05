from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
import uuid

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tokentoll.crypto import generate_rsa_key_pair
from tokentoll.models import Challenge
from tokentoll.routers import challenges as challenges_router
from tokentoll.routers import siteverify as siteverify_router
from tokentoll.services.token_service import decode_verification_token


def compute_commitment(answers: dict[str, str], nonce: str) -> str:
    canonical = json.dumps(answers, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((canonical + nonce).encode()).hexdigest()


@pytest.fixture
def rsa_key_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    private_key, public_key = generate_rsa_key_pair()
    monkeypatch.setattr(
        challenges_router,
        "load_or_generate_private_key",
        lambda _path=None: private_key,
    )
    monkeypatch.setattr(
        siteverify_router, "get_public_key", lambda _path=None: public_key
    )
    return private_key, public_key


@pytest.mark.asyncio
async def test_full_verification_flow(
    client: AsyncClient,
    db_session: AsyncSession,
    registered_site: tuple[str, str],
    challenge_with_answers: tuple[str, dict[str, str], dict[str, str]],
    rsa_key_pair: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey],
) -> None:
    site_key, secret_key = registered_site
    challenge_id, answers, answer_formats = challenge_with_answers
    assert set(answer_formats) == set(answers)

    nonce = "nonce-full-flow"
    commitment = compute_commitment(answers, nonce)
    verify_response = await client.post(
        "/verify",
        json={
            "challenge_id": challenge_id,
            "nonce": nonce,
            "answers": answers,
            "commitment": commitment,
        },
    )

    assert verify_response.status_code == 200
    verify_payload = verify_response.json()
    assert verify_payload["success"] is True
    token = verify_payload["token"]
    assert token

    _, public_key = rsa_key_pair
    claims = decode_verification_token(token, public_key)
    assert claims["sub"] == challenge_id
    assert claims["site_key"] == site_key
    assert isinstance(claims.get("iat"), int)
    assert isinstance(claims.get("exp"), int)
    assert claims.get("jti")

    siteverify_response = await client.post(
        "/siteverify",
        json={"secret_key": secret_key, "token": token},
    )

    assert siteverify_response.status_code == 200
    siteverify_payload = siteverify_response.json()
    assert siteverify_payload["success"] is True
    assert siteverify_payload["challenge_id"] == challenge_id

    challenge = await db_session.get(Challenge, uuid.UUID(challenge_id))
    assert challenge is not None
    assert challenge.solved is True
    assert challenge.solved_at is not None
    assert siteverify_payload["solved_at"] == challenge.solved_at.isoformat()


@pytest.mark.asyncio
async def test_verify_rejects_wrong_answers(
    client: AsyncClient,
    challenge_with_answers: tuple[str, dict[str, str], dict[str, str]],
    rsa_key_pair: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey],
) -> None:
    challenge_id, answers, _ = challenge_with_answers
    wrong_answers = {question_id: "wrong" for question_id in answers}
    nonce = "nonce-wrong-answers"
    commitment = compute_commitment(wrong_answers, nonce)

    response = await client.post(
        "/verify",
        json={
            "challenge_id": challenge_id,
            "nonce": nonce,
            "answers": wrong_answers,
            "commitment": commitment,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"] == "Score below pass threshold"
    assert payload["token"] is None


@pytest.mark.asyncio
async def test_verify_rejects_expired_challenge(
    client: AsyncClient,
    db_session: AsyncSession,
    challenge_with_answers: tuple[str, dict[str, str], dict[str, str]],
    rsa_key_pair: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey],
) -> None:
    challenge_id, answers, _ = challenge_with_answers
    challenge = await db_session.get(Challenge, uuid.UUID(challenge_id))
    assert challenge is not None
    challenge.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db_session.commit()

    nonce = "nonce-expired"
    commitment = compute_commitment(answers, nonce)
    response = await client.post(
        "/verify",
        json={
            "challenge_id": challenge_id,
            "nonce": nonce,
            "answers": answers,
            "commitment": commitment,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"] == "Challenge expired"
    assert payload["token"] is None


@pytest.mark.asyncio
async def test_verify_rejects_replay_nonce(
    client: AsyncClient,
    challenge_with_answers: tuple[str, dict[str, str], dict[str, str]],
    rsa_key_pair: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey],
) -> None:
    challenge_id, answers, _ = challenge_with_answers
    nonce = "nonce-replay"
    commitment = compute_commitment(answers, nonce)

    first_response = await client.post(
        "/verify",
        json={
            "challenge_id": challenge_id,
            "nonce": nonce,
            "answers": answers,
            "commitment": commitment,
        },
    )

    assert first_response.status_code == 200
    assert first_response.json()["success"] is True

    replay_response = await client.post(
        "/verify",
        json={
            "challenge_id": challenge_id,
            "nonce": nonce,
            "answers": answers,
            "commitment": commitment,
        },
    )

    assert replay_response.status_code == 200
    payload = replay_response.json()
    assert payload["success"] is False
    assert payload["error"] == "Nonce already used"
    assert payload["token"] is None


@pytest.mark.asyncio
async def test_verify_rejects_wrong_commitment(
    client: AsyncClient,
    challenge_with_answers: tuple[str, dict[str, str], dict[str, str]],
    rsa_key_pair: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey],
) -> None:
    challenge_id, answers, _ = challenge_with_answers
    nonce = "nonce-wrong-commitment"
    response = await client.post(
        "/verify",
        json={
            "challenge_id": challenge_id,
            "nonce": nonce,
            "answers": answers,
            "commitment": "invalid",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"] == "Invalid commitment"
    assert payload["token"] is None


@pytest.mark.asyncio
async def test_siteverify_rejects_wrong_secret_key(
    client: AsyncClient,
    challenge_with_answers: tuple[str, dict[str, str], dict[str, str]],
    rsa_key_pair: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey],
) -> None:
    challenge_id, answers, _ = challenge_with_answers
    nonce = "nonce-secret-mismatch"
    commitment = compute_commitment(answers, nonce)
    verify_response = await client.post(
        "/verify",
        json={
            "challenge_id": challenge_id,
            "nonce": nonce,
            "answers": answers,
            "commitment": commitment,
        },
    )

    assert verify_response.status_code == 200
    verify_payload = verify_response.json()
    assert verify_payload["success"] is True
    token = verify_payload["token"]
    response = await client.post(
        "/siteverify",
        json={"secret_key": "invalid-secret", "token": token},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"] == "invalid_secret"


@pytest.mark.asyncio
async def test_siteverify_rejects_cross_site_token(
    client: AsyncClient,
    challenge_with_answers: tuple[str, dict[str, str], dict[str, str]],
    rsa_key_pair: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey],
) -> None:
    site_two_response = await client.post(
        "/sites/", json={"name": "Site Two"}
    )
    assert site_two_response.status_code == 201
    site_two_payload = site_two_response.json()
    site_two_secret = site_two_payload["secret_key"]
    challenge_id, answers, _ = challenge_with_answers
    nonce = "nonce-cross-site"
    commitment = compute_commitment(answers, nonce)
    verify_response = await client.post(
        "/verify",
        json={
            "challenge_id": challenge_id,
            "nonce": nonce,
            "answers": answers,
            "commitment": commitment,
        },
    )

    assert verify_response.status_code == 200
    verify_payload = verify_response.json()
    assert verify_payload["success"] is True
    token = verify_payload["token"]
    response = await client.post(
        "/siteverify",
        json={"secret_key": site_two_secret, "token": token},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"] == "site_key_mismatch"
