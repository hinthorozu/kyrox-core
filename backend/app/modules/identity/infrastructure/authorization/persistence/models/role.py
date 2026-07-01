from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BaseModelMixin


class RoleModel(BaseModelMixin, Base):
    __tablename__ = "identity_roles"
    __table_args__ = (
        UniqueConstraint("scope", "slug", name="uq_identity_roles_scope_slug"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
