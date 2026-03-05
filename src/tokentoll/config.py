from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./tokentoll.db"
    secret_key: str = "dev-secret-change-me"
    token_ttl_seconds: int = 300
    challenge_expiry_seconds: int = 600
    challenge_rate_limit_per_minute: int = 60
    challenge_rate_limit_window_seconds: int = 60
    rsa_private_key_path: str | None = None
    debug: bool = False

    model_config = {"env_prefix": "TOKENTOLL_"}


def get_settings() -> Settings:
    return Settings()
