from dataclasses import dataclass
from datetime import datetime

from app.modules.identity.domain.authorization.enums.assignment_status import AssignmentStatus
from app.modules.identity.domain.authorization.exceptions import InvalidRoleError
from app.modules.identity.domain.authorization.value_objects.identity.organization_id import (
    OrganizationId,
)
from app.modules.identity.domain.authorization.value_objects.identity.organization_role_id import (
    OrganizationRoleId,
)
from app.modules.identity.domain.authorization.value_objects.identity.role_id import RoleId


@dataclass
class OrganizationRole:
    id: OrganizationRoleId
    organization_id: OrganizationId
    role_id: RoleId
    status: AssignmentStatus
    is_default: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    def is_active(self) -> bool:
        return self.deleted_at is None and self.status is AssignmentStatus.ACTIVE

    def assert_active(self) -> None:
        if not self.is_active():
            raise InvalidRoleError("Organization role is not active")

    def deactivate(self, at: datetime) -> None:
        self.status = AssignmentStatus.INACTIVE
        self.updated_at = at
