import uuid
from datetime import datetime

from app.modules.identity.domain.authentication.entities.user import User
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.authentication.value_objects.security.email import Email
from app.modules.identity.domain.authorization.entities.role import Role
from app.modules.identity.domain.authorization.enums.role_scope import RoleScope
from app.modules.identity.domain.authorization.value_objects.identity.role_id import RoleId
from app.modules.identity.domain.authorization.value_objects.rbac.role_slug import RoleSlug
from app.modules.identity.domain.organization.entities.organization import Organization
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId
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

    def remove(self, organization_id: OrganizationId) -> None:
        organization = self._by_id.pop(organization_id.value, None)
        if organization is not None:
            self._slugs.discard(organization.slug.value)
            self.items = [item for item in self.items if item.id.value != organization_id.value]

    def get_by_id(self, organization_id: OrganizationId) -> Organization | None:
        return self._by_id.get(organization_id.value)

    def get_by_slug(self, slug: OrganizationSlug) -> Organization | None:
        for organization in self.items:
            if organization.slug.value == slug.value:
                return organization
        return None

    def exists_by_slug(self, slug: OrganizationSlug) -> bool:
        return slug.value in self._slugs


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
