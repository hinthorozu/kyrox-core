from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BaseModelMixin
from app.db.types import UTCDateTime, UUIDPrimaryKey
from app.db.utils import generate_uuid


class UserModel(BaseModelMixin, Base):
    __tablename__ = "identity_users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    is_super_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class OrganizationModel(BaseModelMixin, Base):
    __tablename__ = "identity_organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class MembershipModel(BaseModelMixin, Base):
    __tablename__ = "identity_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_identity_memberships_user_organization"),
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


class SessionModel(Base):
    __tablename__ = "identity_sessions"

    id: Mapped[UUID] = mapped_column(
        UUIDPrimaryKey,
        primary_key=True,
        default=generate_uuid,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUIDPrimaryKey,
        ForeignKey("identity_users.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)


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
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        server_default=func.now(),
    )
