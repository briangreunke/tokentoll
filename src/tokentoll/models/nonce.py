from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tokentoll.models.base import Base

if TYPE_CHECKING:
    from tokentoll.models.challenge import Challenge


class UsedNonce(Base):
    __tablename__ = "used_nonces"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("challenges.id", ondelete="CASCADE"),
        index=True,
    )
    nonce: Mapped[str] = mapped_column(String)
    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    challenge: Mapped[Challenge] = relationship(
        "Challenge",
        back_populates="used_nonces",
    )

    __table_args__ = (
        UniqueConstraint("challenge_id", "nonce", name="uq_challenge_nonce"),
    )
