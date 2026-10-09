import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity.api.authorization.context import AuthorizationContext
from app.modules.identity.api.user_management.routes import (
    get_user_management_context,
    update_user,
)
from app.modules.identity.api.user_management.schemas import ManualUserUpdateRequest
from app.modules.identity.domain.authentication.value_objects.identity.session_id import SessionId
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.access_token import (
    AccessTokenClaims,
)
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.infrastructure.authorization.persistence.models import (
    RoleModel,
    UserRoleModel,
)
from app.modules.identity.infrastructure.organization.persistence.models import OrganizationModel
from app.modules.identity.infrastructure.persistence.models import UserModel


def _claims(user_id: uuid.UUID, email: str) -> AccessTokenClaims:
    now = datetime.now(UTC)
    return AccessTokenClaims(
        sub=UserId(user_id),
        email=Email.create(email),
        sid=SessionId(uuid.uuid4()),
        exp=now,
        iat=now,
        jti=uuid.uuid4(),
    )


def test_granting_super_admin_keeps_organization_and_role(db_session: Session) -> None:
    now = datetime.now(UTC)
    actor_id = uuid.uuid4()
    user_id = uuid.uuid4()
    organization_id = uuid.uuid4()
    role_id = uuid.uuid4()
    db_session.add(OrganizationModel(
        id=organization_id,
        name="Umaay Mimarlık",
        slug="umaay-mimarlik",
        status="active",
    ))
    db_session.add(UserModel(
        id=actor_id,
        email="actor@example.com",
        password_hash="hash",
        status="active",
        is_super_admin=True,
        organization_id=organization_id,
    ))
    db_session.add(UserModel(
        id=user_id,
        email="member@example.com",
        password_hash="hash",
        status="active",
        is_super_admin=False,
        organization_id=organization_id,
    ))
    db_session.add(RoleModel(
        id=role_id,
        name="Organization Admin",
        slug="organization_admin",
        scope="organization",
        is_system=True,
        role_kind="organization",
        organization_id=organization_id,
        template_version=1,
        permissions_customized=False,
        is_assignable=True,
        is_protected=True,
        auto_include_new_permissions=False,
    ))
    db_session.add(UserRoleModel(
        id=uuid.uuid4(),
        user_id=user_id,
        organization_id=organization_id,
        role_id=role_id,
        status="active",
        assigned_at=now,
        revoked_at=None,
        assigned_by=actor_id,
    ))
    db_session.commit()

    result = update_user(
        organization_id,
        user_id,
        ManualUserUpdateRequest(is_super_admin=True),
        AuthorizationContext(
            user_id=actor_id,
            organization_id=organization_id,
            email="actor@example.com",
            is_super_admin=True,
        ),
        db_session,
    )

    stored = db_session.get(UserModel, user_id)
    role = db_session.scalar(select(UserRoleModel).where(UserRoleModel.user_id == user_id))
    assert stored is not None
    assert stored.is_super_admin is True
    assert stored.organization_id == organization_id
    assert role is not None
    assert role.status == "active"
    assert role.revoked_at is None
    assert result.organization_id == organization_id
    assert result.role is not None
    assert result.role.id == role_id


def test_super_admin_context_reports_the_owned_organization(db_session: Session) -> None:
    user_id = uuid.uuid4()
    organization_id = uuid.uuid4()
    db_session.add(OrganizationModel(
        id=organization_id,
        name="Umaay Mimarlık",
        slug="umaay-context",
        status="active",
    ))
    db_session.add(UserModel(
        id=user_id,
        email="owner@example.com",
        password_hash="hash",
        status="active",
        is_super_admin=True,
        organization_id=organization_id,
    ))
    db_session.commit()

    context = get_user_management_context(
        _claims(user_id, "owner@example.com"),
        db_session,
    )

    assert context.is_super_admin is True
    assert context.organization_id == organization_id
    assert any(item.id == organization_id and item.name == "Umaay Mimarlık" for item in context.organizations)
