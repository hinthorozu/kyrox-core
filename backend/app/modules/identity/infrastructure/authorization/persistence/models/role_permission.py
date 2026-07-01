from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UUIDPrimaryKey


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
