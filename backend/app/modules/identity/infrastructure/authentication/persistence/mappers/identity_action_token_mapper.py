from app.modules.identity.domain.authentication.entities.identity_action_token import (
    IdentityActionToken,
)
from app.modules.identity.domain.authentication.enums.identity_action_token_purpose import (
    IdentityActionTokenPurpose,
)
from app.modules.identity.domain.authentication.value_objects.identity.identity_action_token_id import (
    IdentityActionTokenId,
)
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.token_hash import TokenHash
from app.modules.identity.infrastructure.authentication.persistence.models.identity_action_token import (
    IdentityActionTokenModel,
)


class IdentityActionTokenMapper:
    @staticmethod
    def to_domain(model: IdentityActionTokenModel) -> IdentityActionToken:
        return IdentityActionToken(
            id=IdentityActionTokenId(model.id),
            user_id=UserId(model.user_id),
            purpose=IdentityActionTokenPurpose(model.purpose),
            token_hash=TokenHash(model.token_hash),
            expires_at=model.expires_at,
            created_at=model.created_at,
            consumed_at=model.consumed_at,
            invalidated_at=model.invalidated_at,
        )

    @staticmethod
    def to_model(entity: IdentityActionToken) -> IdentityActionTokenModel:
        return IdentityActionTokenModel(
            id=entity.id.value,
            user_id=entity.user_id.value,
            purpose=entity.purpose.value,
            token_hash=entity.token_hash.value,
            expires_at=entity.expires_at,
            created_at=entity.created_at,
            consumed_at=entity.consumed_at,
            invalidated_at=entity.invalidated_at,
        )

    @staticmethod
    def apply_to_model(
        entity: IdentityActionToken,
        model: IdentityActionTokenModel,
    ) -> None:
        model.user_id = entity.user_id.value
        model.purpose = entity.purpose.value
        model.token_hash = entity.token_hash.value
        model.expires_at = entity.expires_at
        model.consumed_at = entity.consumed_at
        model.invalidated_at = entity.invalidated_at
