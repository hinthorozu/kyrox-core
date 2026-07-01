import uuid
from datetime import UTC, datetime, timedelta

from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.membership.entities.membership import Membership
from app.modules.identity.domain.membership.entities.membership_invite import MembershipInvite
from app.modules.identity.domain.membership.enums.membership_status import MembershipStatus
from app.modules.identity.domain.membership.value_objects.identity.invite_id import InviteId
from app.modules.identity.domain.membership.value_objects.identity.membership_id import MembershipId
from app.modules.identity.domain.membership.value_objects.invite.invite_email import InviteEmail
from app.modules.identity.domain.membership.value_objects.invite.invite_token_hash import InviteTokenHash
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId
from app.modules.identity.infrastructure.membership.persistence.mappers.membership_invite_mapper import (
    MembershipInviteMapper,
)
from app.modules.identity.infrastructure.membership.persistence.mappers.membership_mapper import (
    MembershipMapper,
)
from app.modules.identity.infrastructure.membership.persistence.models.membership import MembershipModel
from app.modules.identity.infrastructure.membership.persistence.models.membership_invite import (
    MembershipInviteModel,
)
from app.modules.identity.infrastructure.membership.security.secure_invite_token_service import (
    SecureInviteTokenService,
)


def _now() -> datetime:
    return datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)


def test_membership_mapper_roundtrip() -> None:
    membership = Membership(
        id=MembershipId(uuid.uuid4()),
        user_id=UserId(uuid.uuid4()),
        organization_id=OrganizationId(uuid.uuid4()),
        status=MembershipStatus.ACTIVE,
        invited_at=None,
        joined_at=_now(),
        created_at=_now(),
        updated_at=_now(),
    )

    model = MembershipMapper.to_model(membership)
    assert isinstance(model, MembershipModel)
    restored = MembershipMapper.to_domain(model)
    assert restored.id.value == membership.id.value
    assert restored.joined_at == membership.joined_at


def test_membership_invite_mapper_roundtrip() -> None:
    invite = MembershipInvite(
        id=InviteId(uuid.uuid4()),
        organization_id=OrganizationId(uuid.uuid4()),
        email=InviteEmail.create("invitee@example.com"),
        token_hash=InviteTokenHash(value="hash"),
        invited_by_user_id=UserId(uuid.uuid4()),
        expires_at=_now() + timedelta(days=7),
        accepted_at=None,
        revoked_at=None,
        created_at=_now(),
    )

    model = MembershipInviteMapper.to_model(invite)
    assert isinstance(model, MembershipInviteModel)
    restored = MembershipInviteMapper.to_domain(model)
    assert restored.email.value == invite.email.value


def test_membership_invite_model_metadata() -> None:
    table = MembershipInviteModel.__table__

    assert table.name == "identity_membership_invites"
    assert "token_hash" in {column.name for column in table.columns}


def test_secure_invite_token_service_generates_and_hashes() -> None:
    service = SecureInviteTokenService()
    plain_token = service.generate()
    token_hash = service.hash(plain_token)

    assert plain_token
    assert token_hash.value
    assert service.hash(plain_token).value == token_hash.value
