import re
from dataclasses import dataclass

from app.modules.identity.domain.organization.exceptions import InvalidOrganizationSlugError

_ORGANIZATION_SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9-]{2,62}$")


@dataclass(frozen=True, slots=True)
class OrganizationSlug:
    value: str

    @classmethod
    def create(cls, raw: str) -> "OrganizationSlug":
        normalized = raw.strip().lower()
        if not normalized or not _ORGANIZATION_SLUG_PATTERN.match(normalized):
            raise InvalidOrganizationSlugError("Invalid organization slug")
        return cls(value=normalized)

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise InvalidOrganizationSlugError("Organization slug cannot be empty")
