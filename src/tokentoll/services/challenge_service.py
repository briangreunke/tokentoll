from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from tokentoll.challenges.generator import generate_challenge
from tokentoll.challenges.types import GeneratedChallenge
from tokentoll.config import get_settings
from tokentoll.errors import InvalidSiteKeyError
from tokentoll.models import Challenge
from tokentoll.services.site_service import get_site_by_key


async def create_challenge(
    db: AsyncSession,
    site_key: str,
    ip_address: str | None = None,
) -> tuple[Challenge, GeneratedChallenge]:
    site = await get_site_by_key(db, site_key)
    if site is None or not site.is_active:
        raise InvalidSiteKeyError()

    generated = generate_challenge()
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=settings.challenge_expiry_seconds
    )

    challenge = Challenge(
        site_id=site.id,
        context=generated.context,
        answer_key=json.dumps(
            {question.id: question.expected_answer for question in generated.questions}
        ),
        question_count=len(generated.questions),
        expires_at=expires_at,
        ip_address=ip_address,
    )
    db.add(challenge)
    await db.commit()
    await db.refresh(challenge)
    return challenge, generated
