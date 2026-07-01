import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.membership.entities import Membership, MembershipInvite
from app.modules.identity.domain.membership.enums import MembershipStatus
from app.modules.identity.domain.membership.exceptions import (
    InvalidMembershipTransitionError,
    MembershipInviteAlreadyAcceptedError,
    MembershipInviteExpiredError,
)
from app.modules.identity.domain.membership.value_objects import (
    InviteEmail,
    InviteId,
    InviteTokenHash,
    MembershipId,
)
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId


def _now() -> datetime:
    return datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)


def test_membership_accept_invite() -> None:
    membership = Membership(
        id=MembershipId(uuid.uuid4()),
        user_id=UserId(uuid.uuid4()),
        organization_id=OrganizationId(uuid.uuid4()),
        status=MembershipStatus.INVITED,
        invited_at=_now(),
        joined_at=None,
        created_at=_now(),
        updated_at=_now(),
    )

    membership.accept_invite(_now())
    assert membership.status is MembershipStatus.ACTIVE
    assert membership.joined_at is not None
    assert membership.is_effective() is True


def test_membership_suspend_and_remove() -> None:
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

    membership.suspend(_now())
    assert membership.status is MembershipStatus.SUSPENDED

    membership.status = MembershipStatus.ACTIVE
    membership.remove(_now())
    assert membership.status is MembershipStatus.REMOVED


def test_membership_assert_can_access_organization() -> None:
    membership = Membership(
        id=MembershipId(uuid.uuid4()),
        user_id=UserId(uuid.uuid4()),
        organization_id=OrganizationId(uuid.uuid4()),
        status=MembershipStatus.INVITED,
        invited_at=_now(),
        joined_at=None,
        created_at=_now(),
        updated_at=_now(),
    )

    with pytest.raises(InvalidMembershipTransitionError):
        membership.assert_can_access_organization()


def test_membership_invite_accept_and_expire() -> None:
    now = _now()
    invite = MembershipInvite(
        id=InviteId(uuid.uuid4()),
        organization_id=OrganizationId(uuid.uuid4()),
        email=InviteEmail.create("member@example.com"),
        token_hash=InviteTokenHash("hash"),
        invited_by_user_id=UserId(uuid.uuid4()),
        expires_at=now + timedelta(hours=1),
        accepted_at=None,
        revoked_at=None,
        created_at=now,
    )

    assert invite.is_pending(now) is True
    invite.accept(now)
    assert invite.accepted_at == now

    with pytest.raises(MembershipInviteAlreadyAcceptedError):
        invite.accept(now)


def test_membership_invite_rejects_expired_accept() -> None:
    now = _now()
    invite = MembershipInvite(
        id=InviteId(uuid.uuid4()),
        organization_id=OrganizationId(uuid.uuid4()),
        email=InviteEmail.create("member@example.com"),
        token_hash=InviteTokenHash("hash"),
        invited_by_user_id=UserId(uuid.uuid4()),
        expires_at=now - timedelta(minutes=1),
        accepted_at=None,
        revoked_at=None,
        created_at=now,
    )

    with pytest.raises(MembershipInviteExpiredError):
        invite.accept(now)
