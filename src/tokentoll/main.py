from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tokentoll.routers.challenges import router as challenges_router
from tokentoll.routers.siteverify import router as siteverify_router
from tokentoll.routers.sites import router as sites_router
from tokentoll.routers.well_known import router as well_known_router


def create_app() -> FastAPI:
    app = FastAPI(title="TokenToll", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(sites_router)
    app.include_router(challenges_router)
    app.include_router(siteverify_router)
    app.include_router(well_known_router)

    return app


app = create_app()
