from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.db.utils import utc_now
from app.modules.identity.domain.entities import (
    Membership,
    Organization,
    Permission,
    RefreshToken,
    Role,
    RolePermission,
    Session,
    User,
)
from app.modules.identity.domain.enums import MembershipStatus
from app.modules.identity.infrastructure.persistence.mappers import (
    membership_to_domain,
    membership_to_model,
    organization_to_domain,
    organization_to_model,
    permission_to_domain,
    permission_to_model,
    refresh_token_to_domain,
    refresh_token_to_model,
    role_permission_to_model,
    role_to_domain,
    role_to_model,
    session_to_domain,
    session_to_model,
    user_to_domain,
    user_to_model,
)
from app.modules.identity.infrastructure.persistence.models import (
    MembershipModel,
    OrganizationModel,
    PermissionModel,
    RefreshTokenModel,
    RoleModel,
    RolePermissionModel,
    SessionModel,
    UserModel,
)


class SqlAlchemyUserRepository:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def get_by_id(self, user_id: UUID) -> User | None:
        model = self._session.get(UserModel, user_id)
        if model is None or model.deleted_at is not None:
            return None
        return user_to_domain(model)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(
            UserModel.email == email,
            UserModel.deleted_at.is_(None),
        )
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        return user_to_domain(model)

    def create(self, user: User) -> User:
        model = user_to_model(user)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return user_to_domain(model)

    def update(self, user: User) -> User:
        model = self._session.get(UserModel, user.id)
        if model is None:
            raise ValueError(f"User not found: {user.id}")

        model.email = user.email
        model.password_hash = user.password_hash
        model.status = user.status.value
        model.is_super_admin = user.is_super_admin
        model.updated_at = user.updated_at
        model.deleted_at = user.deleted_at

        self._session.flush()
        self._session.refresh(model)
        return user_to_domain(model)

    def soft_delete(self, user_id: UUID) -> None:
        model = self._session.get(UserModel, user_id)
        if model is None:
            raise ValueError(f"User not found: {user_id}")

        model.deleted_at = utc_now()
        self._session.flush()


class SqlAlchemyOrganizationRepository:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def get_by_id(self, organization_id: UUID) -> Organization | None:
        model = self._session.get(OrganizationModel, organization_id)
        if model is None or model.deleted_at is not None:
            return None
        return organization_to_domain(model)

    def get_by_slug(self, slug: str) -> Organization | None:
        stmt = select(OrganizationModel).where(
            OrganizationModel.slug == slug,
            OrganizationModel.deleted_at.is_(None),
        )
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        return organization_to_domain(model)

    def create(self, organization: Organization) -> Organization:
        model = organization_to_model(organization)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return organization_to_domain(model)

    def update(self, organization: Organization) -> Organization:
        model = self._session.get(OrganizationModel, organization.id)
        if model is None:
            raise ValueError(f"Organization not found: {organization.id}")

        model.name = organization.name
        model.slug = organization.slug
        model.status = organization.status.value
        model.updated_at = organization.updated_at
        model.deleted_at = organization.deleted_at

        self._session.flush()
        self._session.refresh(model)
        return organization_to_domain(model)

    def soft_delete(self, organization_id: UUID) -> None:
        model = self._session.get(OrganizationModel, organization_id)
        if model is None:
            raise ValueError(f"Organization not found: {organization_id}")

        model.deleted_at = utc_now()
        self._session.flush()


class SqlAlchemyMembershipRepository:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def get_by_id(self, membership_id: UUID) -> Membership | None:
        model = self._session.get(MembershipModel, membership_id)
        if model is None or model.deleted_at is not None:
            return None
        return membership_to_domain(model)

    def get_by_user_and_organization(
        self,
        user_id: UUID,
        organization_id: UUID,
    ) -> Membership | None:
        stmt = select(MembershipModel).where(
            MembershipModel.user_id == user_id,
            MembershipModel.organization_id == organization_id,
            MembershipModel.deleted_at.is_(None),
        )
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        return membership_to_domain(model)

    def list_by_user_id(self, user_id: UUID) -> list[Membership]:
        stmt = select(MembershipModel).where(
            MembershipModel.user_id == user_id,
            MembershipModel.deleted_at.is_(None),
        )
        models = self._session.scalars(stmt).all()
        return [membership_to_domain(model) for model in models]

    def list_by_organization_id(self, organization_id: UUID) -> list[Membership]:
        stmt = select(MembershipModel).where(
            MembershipModel.organization_id == organization_id,
            MembershipModel.deleted_at.is_(None),
        )
        models = self._session.scalars(stmt).all()
        return [membership_to_domain(model) for model in models]

    def create(self, membership: Membership) -> Membership:
        model = membership_to_model(membership)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return membership_to_domain(model)

    def update(self, membership: Membership) -> Membership:
        model = self._session.get(MembershipModel, membership.id)
        if model is None:
            raise ValueError(f"Membership not found: {membership.id}")

        model.user_id = membership.user_id
        model.organization_id = membership.organization_id
        model.status = membership.status.value
        model.role_id = membership.role_id
        model.updated_at = membership.updated_at
        model.deleted_at = membership.deleted_at

        self._session.flush()
        self._session.refresh(model)
        return membership_to_domain(model)

    def soft_delete(self, membership_id: UUID) -> None:
        model = self._session.get(MembershipModel, membership_id)
        if model is None:
            raise ValueError(f"Membership not found: {membership_id}")

        model.deleted_at = utc_now()
        self._session.flush()


class SqlAlchemySessionRepository:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def create(self, session_entity: Session) -> Session:
        model = session_to_model(session_entity)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return session_to_domain(model)

    def get_by_id(self, session_id: UUID) -> Session | None:
        model = self._session.get(SessionModel, session_id)
        if model is None:
            return None
        return session_to_domain(model)

    def update(self, session_entity: Session) -> Session:
        model = self._session.get(SessionModel, session_entity.id)
        if model is None:
            raise ValueError(f"Session not found: {session_entity.id}")

        model.updated_at = session_entity.updated_at
        model.revoked_at = session_entity.revoked_at
        model.last_used_at = session_entity.last_used_at
        model.user_agent = session_entity.user_agent
        model.ip_address = session_entity.ip_address

        self._session.flush()
        self._session.refresh(model)
        return session_to_domain(model)

    def revoke(self, session_id: UUID, revoked_at: datetime) -> None:
        model = self._session.get(SessionModel, session_id)
        if model is None:
            raise ValueError(f"Session not found: {session_id}")

        model.revoked_at = revoked_at
        self._session.flush()


class SqlAlchemyRefreshTokenRepository:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def create(self, refresh_token: RefreshToken) -> RefreshToken:
        model = refresh_token_to_model(refresh_token)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return refresh_token_to_domain(model)

    def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        return refresh_token_to_domain(model)

    def revoke(self, refresh_token_id: UUID, revoked_at: datetime) -> None:
        model = self._session.get(RefreshTokenModel, refresh_token_id)
        if model is None:
            raise ValueError(f"Refresh token not found: {refresh_token_id}")

        model.revoked_at = revoked_at
        self._session.flush()


class SqlAlchemyRoleRepository:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def get_by_id(self, role_id: UUID) -> Role | None:
        model = self._session.get(RoleModel, role_id)
        if model is None or model.deleted_at is not None:
            return None
        return role_to_domain(model)

    def get_by_organization_and_slug(self, organization_id: UUID, slug: str) -> Role | None:
        stmt = select(RoleModel).where(
            RoleModel.organization_id == organization_id,
            RoleModel.slug == slug,
            RoleModel.deleted_at.is_(None),
        )
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        return role_to_domain(model)

    def list_by_organization_id(self, organization_id: UUID) -> list[Role]:
        stmt = select(RoleModel).where(
            RoleModel.organization_id == organization_id,
            RoleModel.deleted_at.is_(None),
        )
        models = self._session.scalars(stmt).all()
        return [role_to_domain(model) for model in models]

    def create(self, role: Role) -> Role:
        model = role_to_model(role)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return role_to_domain(model)

    def update(self, role: Role) -> Role:
        model = self._session.get(RoleModel, role.id)
        if model is None:
            raise ValueError(f"Role not found: {role.id}")

        model.organization_id = role.organization_id
        model.name = role.name
        model.slug = role.slug
        model.is_system = role.is_system
        model.updated_at = role.updated_at
        model.deleted_at = role.deleted_at

        self._session.flush()
        self._session.refresh(model)
        return role_to_domain(model)

    def soft_delete(self, role_id: UUID) -> None:
        model = self._session.get(RoleModel, role_id)
        if model is None:
            raise ValueError(f"Role not found: {role_id}")

        model.deleted_at = utc_now()
        self._session.flush()


class SqlAlchemyPermissionRepository:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def get_by_id(self, permission_id: UUID) -> Permission | None:
        model = self._session.get(PermissionModel, permission_id)
        if model is None:
            return None
        return permission_to_domain(model)

    def get_by_code(self, code: str) -> Permission | None:
        stmt = select(PermissionModel).where(PermissionModel.code == code)
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        return permission_to_domain(model)

    def list_all(self) -> list[Permission]:
        models = self._session.scalars(select(PermissionModel)).all()
        return [permission_to_domain(model) for model in models]

    def create(self, permission: Permission) -> Permission:
        model = permission_to_model(permission)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return permission_to_domain(model)


class SqlAlchemyRolePermissionRepository:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def grant(self, role_permission: RolePermission) -> None:
        model = role_permission_to_model(role_permission)
        self._session.merge(model)
        self._session.flush()

    def revoke(self, role_id: UUID, permission_id: UUID) -> None:
        model = self._session.get(
            RolePermissionModel,
            {"role_id": role_id, "permission_id": permission_id},
        )
        if model is not None:
            self._session.delete(model)
            self._session.flush()

    def list_permission_ids_for_role(self, role_id: UUID) -> list[UUID]:
        stmt = select(RolePermissionModel.permission_id).where(
            RolePermissionModel.role_id == role_id
        )
        return list(self._session.scalars(stmt).all())

    def has_permission(self, role_id: UUID, permission_id: UUID) -> bool:
        model = self._session.get(
            RolePermissionModel,
            {"role_id": role_id, "permission_id": permission_id},
        )
        return model is not None


class SqlAlchemyPermissionChecker:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def has_permission(
        self,
        user_id: UUID,
        organization_id: UUID,
        permission_code: str,
    ) -> bool:
        stmt = (
            select(PermissionModel.id)
            .join(
                RolePermissionModel,
                RolePermissionModel.permission_id == PermissionModel.id,
            )
            .join(RoleModel, RoleModel.id == RolePermissionModel.role_id)
            .join(
                MembershipModel,
                MembershipModel.role_id == RoleModel.id,
            )
            .where(
                MembershipModel.user_id == user_id,
                MembershipModel.organization_id == organization_id,
                MembershipModel.status == MembershipStatus.ACTIVE.value,
                MembershipModel.deleted_at.is_(None),
                MembershipModel.role_id.is_not(None),
                RoleModel.deleted_at.is_(None),
                RoleModel.organization_id == organization_id,
                PermissionModel.code == permission_code,
            )
        )
        return self._session.scalars(stmt).first() is not None
