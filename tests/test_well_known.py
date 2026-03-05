from __future__ import annotations

import base64
import uuid

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import AsyncClient

from tokentoll.crypto import generate_rsa_key_pair
from tokentoll.routers import well_known as well_known_router
from tokentoll.services.token_service import (
    create_verification_token,
    decode_verification_token,
)


def _int_from_base64url(value: str) -> int:
    padding = "=" * (-len(value) % 4)
    data = base64.urlsafe_b64decode(f"{value}{padding}")
    return int.from_bytes(data, "big")


def _public_key_from_jwk(jwk: dict[str, str]) -> rsa.RSAPublicKey:
    modulus = _int_from_base64url(jwk["n"])
    exponent = _int_from_base64url(jwk["e"])
    numbers = rsa.RSAPublicNumbers(exponent, modulus)
    return numbers.public_key()


@pytest.mark.asyncio
async def test_jwks_endpoint_returns_jwks_and_cache_header(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, public_key = generate_rsa_key_pair()
    monkeypatch.setattr(
        well_known_router, "get_public_key", lambda _path=None: public_key
    )

    response = await client.get("/.well-known/jwks.json")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "public, max-age=3600"
    payload = response.json()
    assert "keys" in payload
    assert len(payload["keys"]) == 1
    jwk = payload["keys"][0]
    assert jwk["kty"] == "RSA"
    assert jwk["use"] == "sig"
    assert jwk["alg"] == "RS256"
    assert jwk["kid"] == "tokentoll-v1"
    assert jwk["n"]
    assert jwk["e"]


@pytest.mark.asyncio
async def test_jwks_public_key_verifies_token(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_key, public_key = generate_rsa_key_pair()
    monkeypatch.setattr(
        well_known_router, "get_public_key", lambda _path=None: public_key
    )

    response = await client.get("/.well-known/jwks.json")

    assert response.status_code == 200
    jwk = response.json()["keys"][0]
    jwk_public_key = _public_key_from_jwk(jwk)

    token = create_verification_token(
        private_key=private_key,
        challenge_id=str(uuid.uuid4()),
        site_key="site-key",
    )

    claims = decode_verification_token(token, jwk_public_key)

    assert claims["site_key"] == "site-key"
