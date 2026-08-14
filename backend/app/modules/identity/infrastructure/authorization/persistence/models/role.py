from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BaseModelMixin
from app.db.types import UUIDPrimaryKey


class RoleModel(BaseModelMixin, Base):
    __tablename__ = "identity_roles"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    role_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="organization")
    organization_id: Mapped[UUID | None] = mapped_column(
        UUIDPrimaryKey,
        ForeignKey("identity_organizations.id"),
        nullable=True,
    )
    source_template_role_id: Mapped[UUID | None] = mapped_column(
        UUIDPrimaryKey,
        ForeignKey("identity_roles.id"),
        nullable=True,
    )
    template_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source_template_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    permissions_customized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_assignable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_protected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    auto_include_new_permissions: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
