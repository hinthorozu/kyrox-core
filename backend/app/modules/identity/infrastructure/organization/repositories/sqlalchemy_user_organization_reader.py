from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId
from app.modules.identity.infrastructure.persistence.models import UserModel


class SqlAlchemyUserOrganizationReader:
    """Read the single organization stored directly on identity_users."""

    def __init__(self, session: DbSession) -> None:
        self._session = session

    def get_organization_id(self, user_id: UserId) -> OrganizationId | None:
        stmt = select(UserModel.organization_id).where(
            UserModel.id == user_id.value,
            UserModel.deleted_at.is_(None),
        )
        organization_id = self._session.scalar(stmt)
        if organization_id is None:
            return None
        return OrganizationId(organization_id)
