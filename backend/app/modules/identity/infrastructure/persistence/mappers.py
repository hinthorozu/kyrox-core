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
from app.modules.identity.domain.enums import (
    MembershipStatus,
    OrganizationStatus,
    UserStatus,
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


def user_to_domain(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        password_hash=model.password_hash,
        status=UserStatus(model.status),
        is_super_admin=model.is_super_admin,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
    )


def user_to_model(entity: User) -> UserModel:
    return UserModel(
        id=entity.id,
        email=entity.email,
        password_hash=entity.password_hash,
        status=entity.status.value,
        is_super_admin=entity.is_super_admin,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        deleted_at=entity.deleted_at,
    )


def organization_to_domain(model: OrganizationModel) -> Organization:
    return Organization(
        id=model.id,
        name=model.name,
        slug=model.slug,
        status=OrganizationStatus(model.status),
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
    )


def organization_to_model(entity: Organization) -> OrganizationModel:
    return OrganizationModel(
        id=entity.id,
        name=entity.name,
        slug=entity.slug,
        status=entity.status.value,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        deleted_at=entity.deleted_at,
    )


def membership_to_domain(model: MembershipModel) -> Membership:
    return Membership(
        id=model.id,
        user_id=model.user_id,
        organization_id=model.organization_id,
        status=MembershipStatus(model.status),
        created_at=model.created_at,
        updated_at=model.updated_at,
        role_id=model.role_id,
        deleted_at=model.deleted_at,
    )


def membership_to_model(entity: Membership) -> MembershipModel:
    return MembershipModel(
        id=entity.id,
        user_id=entity.user_id,
        organization_id=entity.organization_id,
        status=entity.status.value,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        role_id=entity.role_id,
        deleted_at=entity.deleted_at,
    )


def role_to_domain(model: RoleModel) -> Role:
    return Role(
        id=model.id,
        organization_id=model.organization_id,
        name=model.name,
        slug=model.slug,
        is_system=model.is_system,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
    )


def role_to_model(entity: Role) -> RoleModel:
    return RoleModel(
        id=entity.id,
        organization_id=entity.organization_id,
        name=entity.name,
        slug=entity.slug,
        is_system=entity.is_system,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        deleted_at=entity.deleted_at,
    )


def permission_to_domain(model: PermissionModel) -> Permission:
    return Permission(
        id=model.id,
        code=model.code,
        description=model.description,
        module=model.module,
        is_system=model.is_system,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def permission_to_model(entity: Permission) -> PermissionModel:
    return PermissionModel(
        id=entity.id,
        code=entity.code,
        description=entity.description,
        module=entity.module,
        is_system=entity.is_system,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def role_permission_to_domain(model: RolePermissionModel) -> RolePermission:
    return RolePermission(
        role_id=model.role_id,
        permission_id=model.permission_id,
    )


def role_permission_to_model(entity: RolePermission) -> RolePermissionModel:
    return RolePermissionModel(
        role_id=entity.role_id,
        permission_id=entity.permission_id,
    )


def session_to_domain(model: SessionModel) -> Session:
    return Session(
        id=model.id,
        user_id=model.user_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        revoked_at=model.revoked_at,
        last_used_at=model.last_used_at,
        user_agent=model.user_agent,
        ip_address=model.ip_address,
    )


def session_to_model(entity: Session) -> SessionModel:
    return SessionModel(
        id=entity.id,
        user_id=entity.user_id,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        revoked_at=entity.revoked_at,
        last_used_at=entity.last_used_at,
        user_agent=entity.user_agent,
        ip_address=entity.ip_address,
    )


def refresh_token_to_domain(model: RefreshTokenModel) -> RefreshToken:
    return RefreshToken(
        id=model.id,
        session_id=model.session_id,
        token_hash=model.token_hash,
        expires_at=model.expires_at,
        created_at=model.created_at,
        revoked_at=model.revoked_at,
    )


def refresh_token_to_model(entity: RefreshToken) -> RefreshTokenModel:
    return RefreshTokenModel(
        id=entity.id,
        session_id=entity.session_id,
        token_hash=entity.token_hash,
        expires_at=entity.expires_at,
        created_at=entity.created_at,
        revoked_at=entity.revoked_at,
    )
