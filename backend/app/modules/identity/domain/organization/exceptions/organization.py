class OrganizationError(Exception):
    """Base class for organization domain failures."""


class OrganizationNotFoundError(OrganizationError):
    """Organization lookup failed."""


class DuplicateOrganizationSlugError(OrganizationError):
    """Organization slug is already in use."""


class InactiveOrganizationError(OrganizationError):
    """Organization cannot accept operations in its current state."""


class InvalidOrganizationSlugError(OrganizationError):
    """Organization slug format is invalid."""
