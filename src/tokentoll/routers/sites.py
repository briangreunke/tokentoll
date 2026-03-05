from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from tokentoll.database import get_db
from tokentoll.schemas.site import SiteCreate, SiteCreated
from tokentoll.services.site_service import create_site


router = APIRouter(prefix="/sites", tags=["sites"])


@router.post("/", response_model=SiteCreated, status_code=201)
async def register_site(
    body: SiteCreate, db: AsyncSession = Depends(get_db)
) -> SiteCreated:
    site, raw_secret = await create_site(db, body.name)
    return SiteCreated(
        id=str(site.id),
        name=site.name,
        site_key=site.site_key,
        secret_key=raw_secret,
        token_ttl_seconds=site.token_ttl_seconds,
    )
