from app.modules.identity.domain.entities import Membership, Organization, User
from app.modules.identity.domain.enums import (
    MembershipStatus,
    OrganizationStatus,
    UserStatus,
)
from app.modules.identity.infrastructure.persistence.models import (
    MembershipModel,
    OrganizationModel,
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
        deleted_at=entity.deleted_at,
    )
