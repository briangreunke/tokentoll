from __future__ import annotations

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey

from tokentoll.crypto import (
    generate_rsa_key_pair,
    get_public_key_jwks,
    load_or_generate_private_key,
    serialize_public_key_pem,
)


def _base64url_to_int(value: str) -> int:
    padding = "=" * (-len(value) % 4)
    decoded = base64.urlsafe_b64decode(f"{value}{padding}")
    return int.from_bytes(decoded, "big")


def test_generate_rsa_key_pair_returns_2048_bit_keys() -> None:
    private_key, public_key = generate_rsa_key_pair()

    assert isinstance(private_key, RSAPrivateKey)
    assert isinstance(public_key, RSAPublicKey)
    assert private_key.key_size == 2048
    assert public_key.key_size == 2048


def test_load_or_generate_private_key_creates_and_loads(tmp_path) -> None:
    key_path = tmp_path / "tokentoll.pem"

    generated = load_or_generate_private_key(str(key_path))
    assert key_path.exists()

    loaded = load_or_generate_private_key(str(key_path))
    assert generated.private_numbers().public_numbers == loaded.private_numbers().public_numbers


def test_serialize_public_key_pem_round_trip() -> None:
    private_key, public_key = generate_rsa_key_pair()

    pem = serialize_public_key_pem(public_key)
    assert "BEGIN PUBLIC KEY" in pem

    loaded = serialization.load_pem_public_key(pem.encode())
    assert isinstance(loaded, RSAPublicKey)
    assert loaded.public_numbers() == public_key.public_numbers()


def test_get_public_key_jwks_contains_expected_fields() -> None:
    _, public_key = generate_rsa_key_pair()

    jwks = get_public_key_jwks(public_key)

    assert "keys" in jwks
    assert len(jwks["keys"]) == 1

    jwk = jwks["keys"][0]
    assert jwk["kty"] == "RSA"
    assert jwk["use"] == "sig"
    assert jwk["alg"] == "RS256"
    assert jwk["kid"] == "tokentoll-v1"

    public_numbers = public_key.public_numbers()
    assert _base64url_to_int(jwk["n"]) == public_numbers.n
    assert _base64url_to_int(jwk["e"]) == public_numbers.e
