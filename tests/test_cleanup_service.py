from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from click.testing import CliRunner
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tokentoll.models import Challenge, Site, UsedNonce


@pytest.mark.asyncio
async def test_cleanup_expired_challenges_removes_old_entries(
    db_session: AsyncSession,
) -> None:
    now = datetime.now(timezone.utc)
    site = Site(
        name="Example",
        site_key="site-key",
        secret_key_hash="secret-hash",
    )
    db_session.add(site)
    await db_session.flush()

    old_expired = Challenge(
        site_id=site.id,
        context="{}",
        answer_key="{}",
        question_count=1,
        expires_at=now - timedelta(hours=30),
    )
    recent_expired = Challenge(
        site_id=site.id,
        context="{}",
        answer_key="{}",
        question_count=1,
        expires_at=now - timedelta(hours=2),
    )
    active = Challenge(
        site_id=site.id,
        context="{}",
        answer_key="{}",
        question_count=1,
        expires_at=now + timedelta(hours=2),
    )
    db_session.add_all([old_expired, recent_expired, active])
    await db_session.flush()

    db_session.add_all(
        [
            UsedNonce(challenge_id=old_expired.id, nonce="old-1"),
            UsedNonce(challenge_id=old_expired.id, nonce="old-2"),
            UsedNonce(challenge_id=recent_expired.id, nonce="recent-1"),
        ]
    )
    await db_session.commit()

    from tokentoll.services.cleanup_service import cleanup_expired_challenges

    deleted = await cleanup_expired_challenges(db_session, older_than_hours=24)

    assert deleted == 1

    result = await db_session.execute(select(Challenge))
    remaining_ids = {challenge.id for challenge in result.scalars().all()}
    assert old_expired.id not in remaining_ids
    assert recent_expired.id in remaining_ids
    assert active.id in remaining_ids

    nonce_result = await db_session.execute(select(UsedNonce))
    remaining_nonces = nonce_result.scalars().all()
    assert [nonce.nonce for nonce in remaining_nonces] == ["recent-1"]


@pytest.mark.asyncio
async def test_cleanup_expired_challenges_returns_zero_when_none(
    db_session: AsyncSession,
) -> None:
    now = datetime.now(timezone.utc)
    site = Site(
        name="No Expired",
        site_key="no-expired",
        secret_key_hash="secret-hash",
    )
    db_session.add(site)
    await db_session.flush()

    active = Challenge(
        site_id=site.id,
        context="{}",
        answer_key="{}",
        question_count=1,
        expires_at=now + timedelta(hours=3),
    )
    db_session.add(active)
    await db_session.commit()

    from tokentoll.services.cleanup_service import cleanup_expired_challenges

    deleted = await cleanup_expired_challenges(db_session, older_than_hours=24)

    assert deleted == 0
    remaining = await db_session.get(Challenge, active.id)
    assert remaining is not None


@pytest.mark.asyncio
async def test_cleanup_stats_reports_counts(
    db_session: AsyncSession,
) -> None:
    now = datetime.now(timezone.utc)
    site = Site(
        name="Stats Site",
        site_key="stats-key",
        secret_key_hash="secret-hash",
    )
    db_session.add(site)
    await db_session.flush()

    active = Challenge(
        site_id=site.id,
        context="{}",
        answer_key="{}",
        question_count=1,
        expires_at=now + timedelta(hours=1),
    )
    solved = Challenge(
        site_id=site.id,
        context="{}",
        answer_key="{}",
        question_count=1,
        expires_at=now + timedelta(hours=1),
        solved=True,
        solved_at=now,
    )
    expired = Challenge(
        site_id=site.id,
        context="{}",
        answer_key="{}",
        question_count=1,
        expires_at=now - timedelta(hours=1),
    )
    db_session.add_all([active, solved, expired])
    await db_session.commit()

    from tokentoll.services.cleanup_service import cleanup_stats

    stats = await cleanup_stats(db_session)

    assert stats == {
        "total": 3,
        "expired": 1,
        "solved": 1,
        "active": 1,
    }


@dataclass
class _DummySession:
    label: str = "dummy"


class _DummySessionContext:
    async def __aenter__(self) -> _DummySession:
        return _DummySession()

    async def __aexit__(self, exc_type, exc, traceback) -> bool:
        return False


def test_cli_cleanup_command_invokes_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import tokentoll.cli as cli_module

    calls: dict[str, object] = {}

    async def fake_cleanup(db: _DummySession, older_than_hours: int) -> int:
        calls["db"] = db
        calls["older_than_hours"] = older_than_hours
        return 2

    monkeypatch.setattr(cli_module, "SessionLocal", _DummySessionContext)
    monkeypatch.setattr(cli_module, "cleanup_expired_challenges", fake_cleanup)

    result = CliRunner().invoke(
        cli_module.cli, ["cleanup", "--older-than-hours", "48"]
    )

    assert result.exit_code == 0
    assert "Deleted 2 expired challenges" in result.output
    assert isinstance(calls["db"], _DummySession)
    assert calls["older_than_hours"] == 48


def test_cli_stats_command_outputs_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import tokentoll.cli as cli_module

    async def fake_stats(db: _DummySession) -> dict[str, int]:
        assert isinstance(db, _DummySession)
        return {
            "total": 3,
            "expired": 1,
            "solved": 1,
            "active": 1,
        }

    monkeypatch.setattr(cli_module, "SessionLocal", _DummySessionContext)
    monkeypatch.setattr(cli_module, "cleanup_stats", fake_stats)

    result = CliRunner().invoke(cli_module.cli, ["stats"])

    assert result.exit_code == 0
    assert "Challenge stats:" in result.output
    assert "total: 3" in result.output
    assert "expired: 1" in result.output
    assert "solved: 1" in result.output
    assert "active: 1" in result.output
