from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime, UUIDPrimaryKey


class MembershipInviteModel(Base):
    __tablename__ = "identity_membership_invites"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_identity_membership_invites_token_hash"),
    )

    id: Mapped[UUID] = mapped_column(UUIDPrimaryKey, primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(
        UUIDPrimaryKey,
        ForeignKey("identity_organizations.id"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    invited_by_user_id: Mapped[UUID] = mapped_column(
        UUIDPrimaryKey,
        ForeignKey("identity_users.id"),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
