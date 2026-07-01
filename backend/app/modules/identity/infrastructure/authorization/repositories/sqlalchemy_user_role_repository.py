from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.identity.domain.authorization.entities.user_role import UserRole
from app.modules.identity.domain.authorization.enums.assignment_status import AssignmentStatus
from app.modules.identity.domain.authorization.value_objects.identity.organization_id import (
    OrganizationId,
)
from app.modules.identity.domain.authorization.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authorization.value_objects.identity.user_role_id import UserRoleId
from app.modules.identity.infrastructure.authorization.persistence.mappers.user_role_mapper import (
    UserRoleMapper,
)
from app.modules.identity.infrastructure.authorization.persistence.models.user_role import UserRoleModel


class SqlAlchemyUserRoleRepository:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def add(self, user_role: UserRole) -> UserRole:
        model = UserRoleMapper.to_model(user_role)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return UserRoleMapper.to_domain(model)

    def update(self, user_role: UserRole) -> UserRole:
        model = self._session.get(UserRoleModel, user_role.id.value)
        if model is None:
            raise ValueError(f"User role not found: {user_role.id.value}")

        UserRoleMapper.apply_to_model(user_role, model)
        self._session.flush()
        self._session.refresh(model)
        return UserRoleMapper.to_domain(model)

    def remove(self, user_role_id: UserRoleId) -> None:
        model = self._session.get(UserRoleModel, user_role_id.value)
        if model is None:
            raise ValueError(f"User role not found: {user_role_id.value}")

        self._session.delete(model)
        self._session.flush()

    def get_by_id(self, user_role_id: UserRoleId) -> UserRole | None:
        model = self._session.get(UserRoleModel, user_role_id.value)
        if model is None:
            return None
        return UserRoleMapper.to_domain(model)

    def list_effective_by_user_and_organization(
        self,
        user_id: UserId,
        organization_id: OrganizationId,
    ) -> list[UserRole]:
        stmt = select(UserRoleModel).where(
            UserRoleModel.user_id == user_id.value,
            UserRoleModel.organization_id == organization_id.value,
            UserRoleModel.status == AssignmentStatus.ACTIVE.value,
            UserRoleModel.revoked_at.is_(None),
        )
        models = self._session.scalars(stmt).all()
        return [UserRoleMapper.to_domain(model) for model in models]

    def revoke(self, user_role_id: UserRoleId) -> None:
        model = self._session.get(UserRoleModel, user_role_id.value)
        if model is None:
            raise ValueError(f"User role not found: {user_role_id.value}")

        model.status = AssignmentStatus.INACTIVE.value
        model.revoked_at = datetime.now(tz=UTC)
        self._session.flush()
