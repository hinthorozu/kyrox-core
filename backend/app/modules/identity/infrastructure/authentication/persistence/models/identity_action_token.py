from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime, UUIDPrimaryKey
from app.db.utils import generate_uuid


class IdentityActionTokenModel(Base):
    __tablename__ = "identity_action_tokens"
    __table_args__ = (
        Index(
            "ix_identity_action_tokens_user_purpose",
            "user_id",
            "purpose",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDPrimaryKey,
        primary_key=True,
        default=generate_uuid,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUIDPrimaryKey,
        ForeignKey("identity_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    invalidated_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        server_default=func.now(),
    )
