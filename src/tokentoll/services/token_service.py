from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tokentoll.models import Challenge
from tokentoll.services.site_service import verify_secret_key


def create_verification_token(
    private_key: rsa.RSAPrivateKey,
    challenge_id: str,
    site_key: str,
    ttl_seconds: int = 300,
) -> str:
    """Create a signed JWT token after successful challenge verification."""
    issued_at = datetime.now(timezone.utc)
    iat = int(issued_at.timestamp())
    exp = int((issued_at + timedelta(seconds=ttl_seconds)).timestamp())
    payload = {
        "sub": challenge_id,
        "site_key": site_key,
        "iat": iat,
        "exp": exp,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


def decode_verification_token(
    token: str,
    public_key: rsa.RSAPublicKey,
) -> dict:
    """Decode and verify a JWT token. Raises jwt.InvalidTokenError on failure."""
    return jwt.decode(token, public_key, algorithms=["RS256"])


async def siteverify(
    db: AsyncSession,
    secret_key: str,
    token: str,
    public_key: rsa.RSAPublicKey,
) -> dict[str, str | bool | None]:
    """Full siteverify flow with secret key and JWT validation."""
    site = await verify_secret_key(db, secret_key)
    if site is None:
        return {"success": False, "error": "invalid_secret"}

    try:
        claims = decode_verification_token(token, public_key)
    except jwt.ExpiredSignatureError:
        return {"success": False, "error": "token_expired"}
    except jwt.InvalidTokenError:
        return {"success": False, "error": "invalid_token"}

    if claims.get("site_key") != site.site_key:
        return {"success": False, "error": "site_key_mismatch"}

    challenge_id = claims.get("sub")
    try:
        challenge_uuid = uuid.UUID(str(challenge_id))
    except (TypeError, ValueError):
        return {"success": False, "error": "invalid_challenge"}

    result = await db.execute(
        select(Challenge).where(Challenge.id == challenge_uuid)
    )
    challenge = result.scalar_one_or_none()
    if challenge is None:
        return {"success": False, "error": "challenge_not_found"}
    if not challenge.solved:
        return {"success": False, "error": "challenge_not_solved"}

    solved_at = challenge.solved_at.isoformat() if challenge.solved_at else None
    return {
        "success": True,
        "challenge_id": str(challenge.id),
        "site_key": site.site_key,
        "solved_at": solved_at,
    }
