import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.modules.identity.domain.authentication.entities.user import User
from app.modules.identity.domain.authentication.enums.user_status import UserStatus
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.domain.authentication.value_objects.security.password_hash import PasswordHash
from app.modules.identity.domain.membership.entities.membership import Membership
from app.modules.identity.domain.membership.entities.membership_invite import MembershipInvite
from app.modules.identity.domain.membership.enums.membership_status import MembershipStatus
from app.modules.identity.domain.membership.value_objects.identity.invite_id import InviteId
from app.modules.identity.domain.membership.value_objects.identity.membership_id import MembershipId
from app.modules.identity.domain.membership.value_objects.invite.invite_email import InviteEmail
from app.modules.identity.domain.membership.value_objects.invite.invite_token_hash import InviteTokenHash
from app.modules.identity.domain.organization.entities.organization import Organization
from app.modules.identity.domain.organization.enums.organization_status import OrganizationStatus
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId
from app.modules.identity.domain.organization.value_objects.profile.organization_name import OrganizationName
from app.modules.identity.domain.organization.value_objects.profile.organization_slug import OrganizationSlug
from app.modules.identity.infrastructure.authentication.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)
from app.modules.identity.infrastructure.membership.persistence.models.membership import MembershipModel
from app.modules.identity.infrastructure.membership.persistence.models.membership_invite import (
    MembershipInviteModel,
)
from app.modules.identity.infrastructure.membership.repositories.sqlalchemy_membership_invite_repository import (
    SqlAlchemyMembershipInviteRepository,
)
from app.modules.identity.infrastructure.membership.repositories.sqlalchemy_membership_repository import (
    SqlAlchemyMembershipRepository,
)
from app.modules.identity.infrastructure.organization.persistence.models.organization import OrganizationModel
from app.modules.identity.infrastructure.organization.repositories.sqlalchemy_organization_repository import (
    SqlAlchemyOrganizationRepository,
)
from app.modules.identity.infrastructure.persistence.models import UserModel


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            UserModel.__table__,
            OrganizationModel.__table__,
            MembershipModel.__table__,
            MembershipInviteModel.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _now() -> datetime:
    return datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)


def _seed_user_and_organization(db_session: Session, clock: FixedClock) -> tuple[UserId, OrganizationId]:
    user_repo = SqlAlchemyUserRepository(db_session, clock)
    org_repo = SqlAlchemyOrganizationRepository(db_session, clock)

    user = user_repo.add(
        User(
            id=UserId(uuid.uuid4()),
            email=Email.create("member@example.com"),
            password_hash=PasswordHash("hash"),
            status=UserStatus.ACTIVE,
            created_at=_now(),
            updated_at=_now(),
        )
    )
    organization = org_repo.add(
        Organization(
            id=OrganizationId(uuid.uuid4()),
            name=OrganizationName.create("Acme"),
            slug=OrganizationSlug.create("acme"),
            status=OrganizationStatus.ACTIVE,
            created_at=_now(),
            updated_at=_now(),
        )
    )
    db_session.flush()
    return user.id, organization.id


def test_sqlalchemy_membership_repository_add_update_remove(db_session: Session) -> None:
    clock = FixedClock(_now())
    user_id, organization_id = _seed_user_and_organization(db_session, clock)
    repo = SqlAlchemyMembershipRepository(db_session, clock)

    membership = Membership(
        id=MembershipId(uuid.uuid4()),
        user_id=user_id,
        organization_id=organization_id,
        status=MembershipStatus.ACTIVE,
        invited_at=None,
        joined_at=_now(),
        created_at=_now(),
        updated_at=_now(),
    )
    created = repo.add(membership)
    db_session.commit()
    assert repo.get_by_user_and_organization(user_id, organization_id) is not None

    created.suspend(_now())
    updated = repo.update(created)
    db_session.commit()
    assert updated.status is MembershipStatus.SUSPENDED
    assert repo.list_effective_by_organization_id(organization_id) == []

    repo.remove(created.id)
    db_session.commit()
    assert repo.get_by_id(created.id) is None


def test_sqlalchemy_membership_invite_repository_queries(db_session: Session) -> None:
    clock = FixedClock(_now())
    user_id, organization_id = _seed_user_and_organization(db_session, clock)
    repo = SqlAlchemyMembershipInviteRepository(db_session)
    token_hash = InviteTokenHash(value="abc123")

    invite = MembershipInvite(
        id=InviteId(uuid.uuid4()),
        organization_id=organization_id,
        email=InviteEmail.create("invitee@example.com"),
        token_hash=token_hash,
        invited_by_user_id=user_id,
        expires_at=_now() + timedelta(days=7),
        accepted_at=None,
        revoked_at=None,
        created_at=_now(),
    )
    created = repo.add(invite)
    db_session.commit()

    pending = repo.get_pending_by_token_hash(token_hash)
    assert pending is not None
    assert pending.id.value == created.id.value

    pending_list = repo.list_pending_by_organization_id(organization_id)
    assert len(pending_list) == 1

    pending.accepted_at = _now()
    repo.update(pending)
    db_session.commit()
    assert repo.get_pending_by_token_hash(token_hash) is None

    repo.remove(pending.id)
    db_session.commit()
    assert repo.get_by_id(pending.id) is None
