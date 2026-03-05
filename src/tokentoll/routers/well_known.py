from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from tokentoll.config import get_settings
from tokentoll.crypto import get_public_key, get_public_key_jwks


router = APIRouter(tags=["well-known"])


@router.get("/.well-known/jwks.json")
async def jwks() -> JSONResponse:
    """Return the public key in JWKS format for offline token verification."""
    settings = get_settings()
    public_key = get_public_key(settings.rsa_private_key_path)
    jwks = get_public_key_jwks(public_key)
    return JSONResponse(
        content=jwks,
        headers={"Cache-Control": "public, max-age=3600"},
    )
