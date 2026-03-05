from __future__ import annotations

import logging

import pytest
from httpx import ASGITransport, AsyncClient

from tokentoll.main import create_app


@pytest.mark.asyncio
async def test_request_id_header_is_set_on_success() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")


@pytest.mark.asyncio
async def test_request_id_header_preserves_client_value() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/health", headers={"X-Request-ID": "client-request-id"}
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "client-request-id"


@pytest.mark.asyncio
async def test_generic_exception_handler_returns_500() -> None:
    app = create_app()

    @app.get("/boom")
    async def boom() -> dict[str, str]:
        raise RuntimeError("boom")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {"error": "Internal server error"}
    assert response.headers.get("X-Request-ID")


@pytest.mark.asyncio
async def test_request_logging_includes_expected_fields(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    caplog.set_level(logging.INFO, logger="tokentoll.middleware.logging")

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    request_id = response.headers.get("X-Request-ID")
    assert request_id

    records = [
        record
        for record in caplog.records
        if record.name == "tokentoll.middleware.logging"
    ]
    assert records
    record = records[-1]
    assert record.method == "GET"
    assert record.path == "/health"
    assert record.status_code == 200
    assert isinstance(record.duration_ms, float)
    assert record.request_id == request_id
    assert record.client_ip
