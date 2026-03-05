from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from tokentoll.config import get_settings
from tokentoll.crypto import get_public_key
from tokentoll.database import get_db
from tokentoll.schemas.siteverify import SiteverifyRequest, SiteverifyResponse
from tokentoll.services.token_service import siteverify


router = APIRouter(tags=["siteverify"])


@router.post("/siteverify", response_model=SiteverifyResponse)
async def siteverify_endpoint(
    body: SiteverifyRequest, db: AsyncSession = Depends(get_db)
) -> SiteverifyResponse:
    settings = get_settings()
    result = await siteverify(
        db=db,
        secret_key=body.secret_key,
        token=body.token,
        public_key=get_public_key(settings.rsa_private_key_path),
    )
    return SiteverifyResponse(**result)
