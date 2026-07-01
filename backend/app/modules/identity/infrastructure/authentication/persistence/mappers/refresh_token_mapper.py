from app.modules.identity.domain.authentication.entities.refresh_token import RefreshToken
from app.modules.identity.domain.authentication.enums.refresh_token_revoke_reason import (
    RefreshTokenRevokeReason,
)
from app.modules.identity.domain.authentication.value_objects.client.ip_address import IpAddress
from app.modules.identity.domain.authentication.value_objects.client.user_agent import UserAgent
from app.modules.identity.domain.authentication.value_objects.identity.family_id import FamilyId
from app.modules.identity.domain.authentication.value_objects.identity.refresh_token_id import (
    RefreshTokenId,
)
from app.modules.identity.domain.authentication.value_objects.identity.session_id import SessionId
from app.modules.identity.domain.authentication.value_objects.security.token_hash import TokenHash
from app.modules.identity.infrastructure.authentication.persistence.models.refresh_token import (
    RefreshTokenModel,
)


class RefreshTokenMapper:
    @staticmethod
    def _optional_vo(raw: str | None, factory: type) -> object | None:
        if raw is None:
            return None
        try:
            return factory.create(raw)
        except ValueError:
            return None

    @staticmethod
    def _optional_reason(raw: str | None) -> RefreshTokenRevokeReason | None:
        if raw is None:
            return None
        try:
            return RefreshTokenRevokeReason(raw)
        except ValueError:
            return None

    @staticmethod
    def to_domain(model: RefreshTokenModel) -> RefreshToken:
        return RefreshToken(
            id=RefreshTokenId(model.id),
            session_id=SessionId(model.session_id),
            token_hash=TokenHash(model.token_hash),
            family_id=FamilyId(model.family_id),
            expires_at=model.expires_at,
            created_at=model.created_at,
            rotated_from=RefreshTokenId(model.rotated_from) if model.rotated_from else None,
            used_at=model.used_at,
            revoked_at=model.revoked_at,
            revoked_reason=RefreshTokenMapper._optional_reason(model.revoked_reason),
            reuse_detected_at=model.reuse_detected_at,
            created_by_ip=RefreshTokenMapper._optional_vo(model.created_by_ip, IpAddress),
            created_by_user_agent=RefreshTokenMapper._optional_vo(
                model.created_by_user_agent,
                UserAgent,
            ),
        )

    @staticmethod
    def to_model(entity: RefreshToken) -> RefreshTokenModel:
        return RefreshTokenModel(
            id=entity.id.value,
            session_id=entity.session_id.value,
            token_hash=entity.token_hash.value,
            family_id=entity.family_id.value,
            expires_at=entity.expires_at,
            created_at=entity.created_at,
            rotated_from=entity.rotated_from.value if entity.rotated_from else None,
            used_at=entity.used_at,
            revoked_at=entity.revoked_at,
            revoked_reason=entity.revoked_reason.value if entity.revoked_reason else None,
            reuse_detected_at=entity.reuse_detected_at,
            created_by_ip=entity.created_by_ip.value if entity.created_by_ip else None,
            created_by_user_agent=(
                entity.created_by_user_agent.value if entity.created_by_user_agent else None
            ),
        )

    @staticmethod
    def apply_to_model(entity: RefreshToken, model: RefreshTokenModel) -> None:
        model.token_hash = entity.token_hash.value
        model.family_id = entity.family_id.value
        model.rotated_from = entity.rotated_from.value if entity.rotated_from else None
        model.used_at = entity.used_at
        model.revoked_at = entity.revoked_at
        model.revoked_reason = entity.revoked_reason.value if entity.revoked_reason else None
        model.reuse_detected_at = entity.reuse_detected_at
        model.created_by_ip = entity.created_by_ip.value if entity.created_by_ip else None
        model.created_by_user_agent = (
            entity.created_by_user_agent.value if entity.created_by_user_agent else None
        )
        model.expires_at = entity.expires_at
