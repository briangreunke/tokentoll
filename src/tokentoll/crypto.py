from __future__ import annotations

import base64
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_rsa_key_pair() -> tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    """Generate a new RSA key pair for JWT signing."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def load_or_generate_private_key(path: str | None) -> rsa.RSAPrivateKey:
    """Load private key from PEM file, or generate and save if not exists."""
    if path is None:
        private_key, _ = generate_rsa_key_pair()
        return private_key

    key_path = Path(path)
    if key_path.exists():
        key_bytes = key_path.read_bytes()
        return serialization.load_pem_private_key(key_bytes, password=None)

    private_key, _ = generate_rsa_key_pair()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    key_path.write_bytes(key_bytes)
    return private_key


def serialize_public_key_pem(public_key: rsa.RSAPublicKey) -> str:
    """Serialize public key to PEM string (for customer distribution)."""
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return pem.decode()


def get_public_key_jwks(public_key: rsa.RSAPublicKey) -> dict:
    """Return public key in JWKS format for /.well-known/jwks.json endpoint."""
    numbers = public_key.public_numbers()

    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": "tokentoll-v1",
                "n": _int_to_base64url(numbers.n),
                "e": _int_to_base64url(numbers.e),
            }
        ]
    }


def _int_to_base64url(value: int) -> str:
    byte_length = (value.bit_length() + 7) // 8
    data = value.to_bytes(byte_length, "big")
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")
