from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tokentoll.challenges.types import GeneratedChallenge, Question
from tokentoll.middleware import rate_limit
from tokentoll.services import challenge_service
from tokentoll.services.site_service import create_site


def _sample_generated_challenge() -> GeneratedChallenge:
    return GeneratedChallenge(
        seed="seed",
        puzzle_type="logic",
        context="API context",
        questions=[
            Question(
                id="q1",
                text="Question one?",
                expected_answer="alpha",
                answer_format="single_word",
            )
        ],
        estimated_tokens=11,
    )


def test_sliding_window_rate_limiter_expires_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    limiter = rate_limit.SlidingWindowRateLimiter(
        max_requests=2, window_seconds=10
    )
    current_time = [0.0]

    def fake_time() -> float:
        return current_time[0]

    monkeypatch.setattr(rate_limit, "time", fake_time)

    assert limiter.is_allowed("ip-1") is True
    assert limiter.remaining("ip-1") == 1
    assert limiter.is_allowed("ip-1") is True
    assert limiter.remaining("ip-1") == 0
    assert limiter.is_allowed("ip-1") is False
    assert limiter.reset_time("ip-1") == 10

    current_time[0] = 11
    assert limiter.is_allowed("ip-1") is True
    assert limiter.remaining("ip-1") == 1


def test_sliding_window_rate_limiter_is_per_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    limiter = rate_limit.SlidingWindowRateLimiter(
        max_requests=1, window_seconds=60
    )

    monkeypatch.setattr(rate_limit, "time", lambda: 5.0)

    assert limiter.is_allowed("ip-1") is True
    assert limiter.is_allowed("ip-1") is False
    assert limiter.is_allowed("ip-2") is True
    assert limiter.remaining("ip-2") == 0


@pytest.mark.asyncio
async def test_challenge_rate_limit_blocks_over_limit(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    site, _ = await create_site(db_session, "Rate Limit Site")
    generated = _sample_generated_challenge()

    monkeypatch.setattr(
        challenge_service, "generate_challenge", lambda: generated
    )
    monkeypatch.setattr(rate_limit, "time", lambda: 100.0)
    limiter = rate_limit.SlidingWindowRateLimiter(
        max_requests=2, window_seconds=30
    )
    monkeypatch.setattr(rate_limit, "challenge_rate_limiter", limiter)

    for _ in range(2):
        response = await client.post(
            "/challenge", json={"site_key": site.site_key}
        )
        assert response.status_code == 201

    response = await client.post(
        "/challenge", json={"site_key": site.site_key}
    )

    assert response.status_code == 429
    assert response.json()["detail"]["error"] == "rate_limit_exceeded"
    assert response.headers["X-RateLimit-Remaining"] == "0"
    assert response.headers["Retry-After"] == "30"


@pytest.mark.asyncio
async def test_rate_limit_not_applied_to_verify_endpoints(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    site, _ = await create_site(db_session, "Rate Limit Site")
    limiter = rate_limit.SlidingWindowRateLimiter(
        max_requests=0, window_seconds=60
    )
    monkeypatch.setattr(rate_limit, "challenge_rate_limiter", limiter)

    response = await client.post(
        "/challenge", json={"site_key": site.site_key}
    )
    assert response.status_code == 429

    verify_response = await client.post("/verify", json={})
    assert verify_response.status_code == 422

    siteverify_response = await client.post("/siteverify", json={})
    assert siteverify_response.status_code == 422
