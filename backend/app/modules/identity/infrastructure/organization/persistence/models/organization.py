from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BaseModelMixin


class OrganizationModel(BaseModelMixin, Base):
    __tablename__ = "identity_organizations"
    __table_args__ = (UniqueConstraint("slug", name="uq_identity_organizations_slug"),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
