from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime, UUIDPrimaryKey
from app.db.utils import generate_uuid


class RefreshTokenModel(Base):
    __tablename__ = "identity_refresh_tokens"

    id: Mapped[UUID] = mapped_column(
        UUIDPrimaryKey,
        primary_key=True,
        default=generate_uuid,
    )
    session_id: Mapped[UUID] = mapped_column(
        UUIDPrimaryKey,
        ForeignKey("identity_sessions.id"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    family_id: Mapped[UUID] = mapped_column(
        UUIDPrimaryKey,
        nullable=False,
        default=generate_uuid,
    )
    rotated_from: Mapped[UUID | None] = mapped_column(
        UUIDPrimaryKey,
        ForeignKey("identity_refresh_tokens.id"),
        nullable=True,
    )
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reuse_detected_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_by_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_by_user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        server_default=func.now(),
    )
