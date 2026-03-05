from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tokentoll.models import Challenge, UsedNonce


async def cleanup_expired_challenges(
    db: AsyncSession,
    older_than_hours: int = 24,
) -> int:
    """Delete challenges that expired more than older_than_hours ago.

    Also deletes associated used_nonces. Returns the number of deleted challenges.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)

    expired_ids = select(Challenge.id).where(Challenge.expires_at <= cutoff)
    count_stmt = select(func.count()).select_from(Challenge).where(
        Challenge.expires_at <= cutoff
    )
    deleted_count = await db.scalar(count_stmt)
    if deleted_count is None or deleted_count == 0:
        return 0

    await db.execute(
        delete(UsedNonce).where(UsedNonce.challenge_id.in_(expired_ids))
    )
    await db.execute(delete(Challenge).where(Challenge.id.in_(expired_ids)))
    await db.commit()
    return int(deleted_count)


async def cleanup_stats(db: AsyncSession) -> dict[str, int]:
    """Return stats: total challenges, expired, solved, active."""
    now = datetime.now(timezone.utc)

    total_stmt = select(func.count()).select_from(Challenge)
    expired_stmt = select(func.count()).select_from(Challenge).where(
        Challenge.expires_at <= now
    )
    solved_stmt = select(func.count()).select_from(Challenge).where(
        Challenge.solved.is_(True)
    )
    active_stmt = select(func.count()).select_from(Challenge).where(
        Challenge.expires_at > now,
        Challenge.solved.is_(False),
    )

    total = await db.scalar(total_stmt) or 0
    expired = await db.scalar(expired_stmt) or 0
    solved = await db.scalar(solved_stmt) or 0
    active = await db.scalar(active_stmt) or 0

    return {
        "total": int(total),
        "expired": int(expired),
        "solved": int(solved),
        "active": int(active),
    }
