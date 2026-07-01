from dataclasses import dataclass

from app.modules.identity.domain.organization.exceptions import InvalidOrganizationSlugError
from app.modules.identity.domain.organization.value_objects.profile.organization_name import OrganizationName
from app.modules.identity.domain.organization.value_objects.profile.organization_slug import OrganizationSlug


@dataclass(frozen=True, slots=True)
class OrganizationNamingPolicy:
    def normalize_name(self, raw: str) -> OrganizationName:
        return OrganizationName.create(raw)

    def normalize_slug(self, raw: str) -> OrganizationSlug:
        try:
            return OrganizationSlug.create(raw)
        except InvalidOrganizationSlugError:
            raise
        except ValueError as exc:
            raise InvalidOrganizationSlugError(str(exc)) from exc
