from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BaseModelMixin
from app.db.types import UTCDateTime, UUIDPrimaryKey


class MembershipModel(BaseModelMixin, Base):
    __tablename__ = "identity_memberships"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "organization_id",
            name="uq_identity_memberships_user_organization",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        UUIDPrimaryKey,
        ForeignKey("identity_users.id"),
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(
        UUIDPrimaryKey,
        ForeignKey("identity_organizations.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    invited_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    joined_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
