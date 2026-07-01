import uuid
from datetime import datetime

from app.modules.identity.domain.authentication.entities.user import User
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.domain.authorization.entities.organization_role import OrganizationRole
from app.modules.identity.domain.authorization.entities.role import Role
from app.modules.identity.domain.authorization.entities.user_role import UserRole
from app.modules.identity.domain.authorization.enums.role_scope import RoleScope
from app.modules.identity.domain.authorization.value_objects.identity.organization_id import OrganizationId
from app.modules.identity.domain.authorization.value_objects.identity.organization_role_id import (
    OrganizationRoleId,
)
from app.modules.identity.domain.authorization.value_objects.identity.role_id import RoleId
from app.modules.identity.domain.authorization.value_objects.identity.user_role_id import UserRoleId
from app.modules.identity.domain.authorization.value_objects.rbac.role_slug import RoleSlug
from app.modules.identity.domain.membership.entities.membership import Membership
from app.modules.identity.domain.membership.entities.membership_invite import MembershipInvite
from app.modules.identity.domain.membership.value_objects.identity.invite_id import InviteId
from app.modules.identity.domain.membership.value_objects.identity.membership_id import MembershipId
from app.modules.identity.domain.membership.value_objects.invite.invite_token_hash import InviteTokenHash
from app.modules.identity.domain.organization.entities.organization import Organization
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId as OrgId
from app.modules.identity.domain.organization.value_objects.profile.organization_slug import OrganizationSlug


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class SequenceIdGenerator:
    def __init__(self, values: list[uuid.UUID]) -> None:
        self._values = values
        self._index = 0

    def generate_uuid(self) -> uuid.UUID:
        value = self._values[self._index % len(self._values)]
        self._index += 1
        return value


class InMemoryUserRepository:
    def __init__(self, users: list[User] | None = None) -> None:
        self._users_by_id = {user.id: user for user in users or []}
        self._users_by_email = {user.email.value: user for user in users or []}

    def add(self, user: User) -> User:
        self._users_by_id[user.id] = user
        self._users_by_email[user.email.value] = user
        return user

    def update(self, user: User) -> User:
        return self.add(user)

    def remove(self, user_id: UserId) -> None:
        user = self._users_by_id.pop(user_id, None)
        if user is not None:
            self._users_by_email.pop(user.email.value, None)

    def get_by_id(self, user_id: UserId) -> User | None:
        return self._users_by_id.get(user_id)

    def get_by_email(self, email: Email) -> User | None:
        return self._users_by_email.get(email.value)


class InMemoryOrganizationRepository:
    def __init__(self) -> None:
        self.items: list[Organization] = []
        self._by_id: dict[uuid.UUID, Organization] = {}
        self._slugs: set[str] = set()

    def add_slug(self, slug: OrganizationSlug) -> None:
        self._slugs.add(slug.value)

    def add(self, organization: Organization) -> Organization:
        self.items.append(organization)
        self._by_id[organization.id.value] = organization
        self._slugs.add(organization.slug.value)
        return organization

    def update(self, organization: Organization) -> Organization:
        self._by_id[organization.id.value] = organization
        return organization

    def remove(self, organization_id: OrgId) -> None:
        organization = self._by_id.pop(organization_id.value, None)
        if organization is not None:
            self._slugs.discard(organization.slug.value)
            self.items = [item for item in self.items if item.id.value != organization_id.value]

    def get_by_id(self, organization_id: OrgId) -> Organization | None:
        return self._by_id.get(organization_id.value)

    def get_by_slug(self, slug: OrganizationSlug) -> Organization | None:
        for organization in self.items:
            if organization.slug.value == slug.value:
                return organization
        return None

    def exists_by_slug(self, slug: OrganizationSlug) -> bool:
        return slug.value in self._slugs


class InMemoryMembershipRepository:
    def __init__(self) -> None:
        self.items: list[Membership] = []

    def add(self, membership: Membership) -> Membership:
        self.items.append(membership)
        return membership

    def update(self, membership: Membership) -> Membership:
        for index, current in enumerate(self.items):
            if current.id.value == membership.id.value:
                self.items[index] = membership
                return membership
        self.items.append(membership)
        return membership

    def remove(self, membership_id: MembershipId) -> None:
        self.items = [item for item in self.items if item.id.value != membership_id.value]

    def get_by_id(self, membership_id: MembershipId) -> Membership | None:
        for membership in self.items:
            if membership.id.value == membership_id.value:
                return membership
        return None

    def get_by_user_and_organization(
        self,
        user_id: UserId,
        organization_id: OrganizationId,
    ) -> Membership | None:
        for membership in self.items:
            if (
                membership.user_id.value == user_id.value
                and membership.organization_id.value == organization_id.value
            ):
                return membership
        return None

    def list_by_user_id(self, user_id: UserId) -> list[Membership]:
        return [item for item in self.items if item.user_id.value == user_id.value]

    def list_by_organization_id(self, organization_id: OrganizationId) -> list[Membership]:
        return [
            item for item in self.items if item.organization_id.value == organization_id.value
        ]

    def list_effective_by_organization_id(
        self,
        organization_id: OrganizationId,
    ) -> list[Membership]:
        return [
            item
            for item in self.items
            if item.organization_id.value == organization_id.value and item.is_effective()
        ]


class InMemoryMembershipInviteRepository:
    def __init__(self) -> None:
        self.items: list[MembershipInvite] = []

    def add(self, invite: MembershipInvite) -> MembershipInvite:
        self.items.append(invite)
        return invite

    def update(self, invite: MembershipInvite) -> MembershipInvite:
        for index, current in enumerate(self.items):
            if current.id.value == invite.id.value:
                self.items[index] = invite
                return invite
        self.items.append(invite)
        return invite

    def remove(self, invite_id: InviteId) -> None:
        self.items = [item for item in self.items if item.id.value != invite_id.value]

    def get_by_id(self, invite_id: InviteId) -> MembershipInvite | None:
        for invite in self.items:
            if invite.id.value == invite_id.value:
                return invite
        return None

    def get_pending_by_token_hash(self, token_hash: InviteTokenHash) -> MembershipInvite | None:
        for invite in self.items:
            if invite.token_hash.value == token_hash.value and invite.accepted_at is None:
                return invite
        return None

    def list_pending_by_organization_id(
        self,
        organization_id: OrganizationId,
    ) -> list[MembershipInvite]:
        return [
            invite
            for invite in self.items
            if invite.organization_id.value == organization_id.value and invite.accepted_at is None
        ]


class InMemoryRoleRepository:
    def __init__(self) -> None:
        self.items: list[Role] = []

    def add(self, role: Role) -> Role:
        self.items.append(role)
        return role

    def update(self, role: Role) -> Role:
        return role

    def remove(self, role_id: RoleId) -> None:
        self.items = [item for item in self.items if item.id.value != role_id.value]

    def get_by_id(self, role_id: RoleId) -> Role | None:
        for role in self.items:
            if role.id.value == role_id.value:
                return role
        return None

    def get_by_slug(self, slug: RoleSlug, scope: RoleScope) -> Role | None:
        for role in self.items:
            if role.slug.value == slug.value and role.scope is scope:
                return role
        return None

    def list_system_roles(self) -> list[Role]:
        return [role for role in self.items if role.is_system]


class InMemoryOrganizationRoleRepository:
    def __init__(self) -> None:
        self.items: list[OrganizationRole] = []

    def add(self, organization_role: OrganizationRole) -> OrganizationRole:
        self.items.append(organization_role)
        return organization_role

    def update(self, organization_role: OrganizationRole) -> OrganizationRole:
        return organization_role

    def remove(self, organization_role_id: OrganizationRoleId) -> None:
        self.items = [
            item for item in self.items if item.id.value != organization_role_id.value
        ]

    def get_by_id(self, organization_role_id: OrganizationRoleId) -> OrganizationRole | None:
        for item in self.items:
            if item.id.value == organization_role_id.value:
                return item
        return None

    def get_by_organization_and_role(
        self,
        organization_id: OrganizationId,
        role_id: RoleId,
    ) -> OrganizationRole | None:
        for item in self.items:
            if (
                item.organization_id.value == organization_id.value
                and item.role_id.value == role_id.value
            ):
                return item
        return None

    def list_active_by_organization(
        self,
        organization_id: OrganizationId,
    ) -> list[OrganizationRole]:
        return [
            item
            for item in self.items
            if item.organization_id.value == organization_id.value and item.is_active()
        ]


class InMemoryUserRoleRepository:
    def __init__(self) -> None:
        self.items: list[UserRole] = []

    def add(self, user_role: UserRole) -> UserRole:
        self.items.append(user_role)
        return user_role

    def update(self, user_role: UserRole) -> UserRole:
        return user_role

    def remove(self, user_role_id: UserRoleId) -> None:
        self.items = [item for item in self.items if item.id.value != user_role_id.value]

    def get_by_id(self, user_role_id: UserRoleId) -> UserRole | None:
        for item in self.items:
            if item.id.value == user_role_id.value:
                return item
        return None

    def list_effective_by_user_and_organization(
        self,
        user_id: UserId,
        organization_id: OrganizationId,
    ) -> list[UserRole]:
        return [
            item
            for item in self.items
            if (
                item.user_id.value == user_id.value
                and item.organization_id.value == organization_id.value
                and item.is_effective()
            )
        ]

    def revoke(self, user_role_id: UserRoleId) -> None:
        for item in self.items:
            if item.id.value == user_role_id.value:
                from datetime import UTC

                item.revoke(datetime.now(tz=UTC))
