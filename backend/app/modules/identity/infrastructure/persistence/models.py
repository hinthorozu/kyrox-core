from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BaseModelMixin


class UserModel(BaseModelMixin, Base):
    __tablename__ = "identity_users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    is_super_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


from app.modules.identity.infrastructure.authentication.persistence.models.refresh_token import (
    RefreshTokenModel,
)
from app.modules.identity.infrastructure.authentication.persistence.models.session import SessionModel
from app.modules.identity.infrastructure.authorization.persistence.models import (
    OrganizationRoleModel,
    PermissionGroupModel,
    PermissionModel,
    RoleModel,
    RolePermissionModel,
    UserRoleModel,
)
from app.modules.identity.infrastructure.membership.persistence.models.membership import MembershipModel
from app.modules.identity.infrastructure.organization.persistence.models.organization import OrganizationModel
