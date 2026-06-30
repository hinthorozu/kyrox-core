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


class RoleModel(BaseModelMixin, Base):
    __tablename__ = "identity_roles"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_identity_roles_organization_slug"),
    )

    organization_id: Mapped[UUID | None] = mapped_column(
        UUIDPrimaryKey,
        ForeignKey("identity_organizations.id"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class PermissionModel(Base):
    __tablename__ = "identity_permissions"

    id: Mapped[UUID] = mapped_column(
        UUIDPrimaryKey,
        primary_key=True,
        default=generate_uuid,
    )
    code: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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


class RolePermissionModel(Base):
    __tablename__ = "identity_role_permissions"

    role_id: Mapped[UUID] = mapped_column(
        UUIDPrimaryKey,
        ForeignKey("identity_roles.id"),
        primary_key=True,
    )
    permission_id: Mapped[UUID] = mapped_column(
        UUIDPrimaryKey,
        ForeignKey("identity_permissions.id"),
        primary_key=True,
    )


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
    role_id: Mapped[UUID | None] = mapped_column(
        UUIDPrimaryKey,
        ForeignKey("identity_roles.id"),
        nullable=True,
    )


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
