from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tokentoll.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from tokentoll.models.nonce import UsedNonce


class Challenge(TimestampMixin, Base):
    __tablename__ = "challenges"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sites.id")
    )
    context: Mapped[str] = mapped_column(Text)
    answer_key: Mapped[str] = mapped_column(Text)
    question_count: Mapped[int]
    pass_threshold: Mapped[float] = mapped_column(default=0.8)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    solved: Mapped[bool] = mapped_column(default=False)
    solved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)

    used_nonces: Mapped[list[UsedNonce]] = relationship(
        "UsedNonce",
        back_populates="challenge",
        cascade="all, delete-orphan",
    )
