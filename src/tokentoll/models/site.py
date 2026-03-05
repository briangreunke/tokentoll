from __future__ import annotations

import uuid

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from tokentoll.models.base import Base, TimestampMixin


class Site(TimestampMixin, Base):
    __tablename__ = "sites"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String)
    site_key: Mapped[str] = mapped_column(String, unique=True, index=True)
    secret_key_hash: Mapped[str] = mapped_column(String)
    token_ttl_seconds: Mapped[int] = mapped_column(default=300)
    is_active: Mapped[bool] = mapped_column(default=True)
    challenge_rate_limit: Mapped[int] = mapped_column(default=60)
