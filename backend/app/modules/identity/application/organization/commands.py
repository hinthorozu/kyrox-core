from dataclasses import dataclass

from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId


@dataclass(frozen=True, slots=True)
class CreateOrganizationCommand:
    owner_user_id: UserId
    name: str
    slug: str


@dataclass(frozen=True, slots=True)
class GetOrganizationCommand:
    organization_id: OrganizationId


@dataclass(frozen=True, slots=True)
class UpdateOrganizationCommand:
    organization_id: OrganizationId
    name: str | None = None


@dataclass(frozen=True, slots=True)
class SuspendOrganizationCommand:
    organization_id: OrganizationId
