from sqlalchemy.orm import Session as DbSession

from app.modules.identity.domain.authentication.enums.user_status import UserStatus
from app.modules.identity.domain.authorization.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authorization.value_objects.rbac.platform_user_snapshot import (
    PlatformUserSnapshot,
)
from app.modules.identity.infrastructure.persistence.models import UserModel


class SqlAlchemyPlatformUserReader:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def get_snapshot(self, user_id: UserId) -> PlatformUserSnapshot | None:
        model = self._session.get(UserModel, user_id.value)
        if model is None or model.deleted_at is not None:
            return None

        return PlatformUserSnapshot(
            user_id=user_id,
            is_active=UserStatus(model.status) is UserStatus.ACTIVE,
            is_super_admin=model.is_super_admin,
            is_deleted=False,
        )
