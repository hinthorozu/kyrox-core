from uuid import UUID

from app.modules.identity.domain.authentication.entities.user import User
from app.modules.identity.domain.authentication.enums.user_status import UserStatus
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.domain.authentication.value_objects.security.password_hash import (
    PasswordHash,
)
from app.modules.identity.infrastructure.persistence.models import UserModel


class UserMapper:
    @staticmethod
    def to_domain(model: UserModel) -> User:
        return User(
            id=UserId(model.id),
            email=Email(value=model.email),
            password_hash=PasswordHash(model.password_hash) if model.password_hash else None,
            status=UserStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    @staticmethod
    def to_model(entity: User) -> UserModel:
        return UserModel(
            id=entity.id.value,
            email=entity.email.value,
            password_hash=entity.password_hash.value if entity.password_hash else None,
            status=entity.status.value,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )

    @staticmethod
    def apply_to_model(entity: User, model: UserModel) -> None:
        model.email = entity.email.value
        model.password_hash = entity.password_hash.value if entity.password_hash else None
        model.status = entity.status.value
        model.updated_at = entity.updated_at
        model.deleted_at = entity.deleted_at
