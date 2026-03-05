from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tokentoll.config import get_settings
from tokentoll.errors import TokenTollError, generic_error_handler, tokentoll_error_handler
from tokentoll.middleware.logging import RequestLoggingMiddleware
from tokentoll.middleware.request_id import RequestIdMiddleware
from tokentoll.routers.challenges import router as challenges_router
from tokentoll.routers.siteverify import router as siteverify_router
from tokentoll.routers.sites import router as sites_router
from tokentoll.routers.well_known import router as well_known_router


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    app = FastAPI(title="TokenToll", version="0.1.0")
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(TokenTollError, tokentoll_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(sites_router)
    app.include_router(challenges_router)
    app.include_router(siteverify_router)
    app.include_router(well_known_router)

    return app


app = create_app()
