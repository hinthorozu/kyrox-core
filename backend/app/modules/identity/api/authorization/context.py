from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class AuthorizationContext:
    user_id: UUID
    organization_id: UUID
    email: str


@dataclass(frozen=True)
class AuthenticatedOrganizationContext:
    user_id: UUID
    organization_id: UUID
    email: str
    session_id: UUID
