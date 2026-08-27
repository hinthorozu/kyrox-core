from enum import StrEnum


class OrganizationStatus(StrEnum):
    PENDING_ACTIVATION = "pending_activation"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"
