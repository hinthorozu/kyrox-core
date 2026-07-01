from typing import Any, Protocol
from uuid import UUID


class OrganizationSettingReaderPort(Protocol):
    """Read-only port for organization-scoped settings values."""

    def get_organization_setting_value(
        self,
        organization_id: UUID,
        key: str,
    ) -> Any | None: ...
