from dataclasses import dataclass
from datetime import datetime

from app.modules.identity.domain.membership.value_objects.identity.membership_id import MembershipId
from app.modules.identity.domain.organization.enums.organization_status import OrganizationStatus
from app.modules.identity.domain.organization.value_objects.identity.organization_id import OrganizationId


@dataclass(frozen=True, slots=True)
class OrganizationResult:
    organization_id: OrganizationId
    name: str
    slug: str
    status: OrganizationStatus
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class CreateOrganizationResult:
    organization: OrganizationResult
    membership_id: MembershipId
