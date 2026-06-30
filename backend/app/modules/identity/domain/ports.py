from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.modules.identity.domain.entities import (
    Membership,
    Organization,
    Permission,
    RefreshToken,
    Role,
    RolePermission,
    Session,
    User,
)


@dataclass(frozen=True)
class AccessTokenClaims:
    sub: UUID
    email: str
    sid: UUID
    exp: datetime
    iat: datetime
    jti: UUID


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class TokenService(Protocol):
    def create_access_token(self, claims: AccessTokenClaims) -> str: ...

    def decode_access_token(self, token: str) -> AccessTokenClaims: ...


class RefreshTokenService(Protocol):
    def generate(self) -> str: ...

    def hash_token(self, token: str) -> str: ...


class UserRepository(Protocol):
    def get_by_id(self, user_id: UUID) -> User | None: ...

    def get_by_email(self, email: str) -> User | None: ...

    def create(self, user: User) -> User: ...

    def update(self, user: User) -> User: ...

    def soft_delete(self, user_id: UUID) -> None: ...


class OrganizationRepository(Protocol):
    def get_by_id(self, organization_id: UUID) -> Organization | None: ...

    def get_by_slug(self, slug: str) -> Organization | None: ...

    def create(self, organization: Organization) -> Organization: ...

    def update(self, organization: Organization) -> Organization: ...

    def soft_delete(self, organization_id: UUID) -> None: ...


class MembershipRepository(Protocol):
    def get_by_id(self, membership_id: UUID) -> Membership | None: ...

    def get_by_user_and_organization(
        self,
        user_id: UUID,
        organization_id: UUID,
    ) -> Membership | None: ...

    def list_by_user_id(self, user_id: UUID) -> list[Membership]: ...

    def list_by_organization_id(self, organization_id: UUID) -> list[Membership]: ...

    def create(self, membership: Membership) -> Membership: ...

    def update(self, membership: Membership) -> Membership: ...

    def soft_delete(self, membership_id: UUID) -> None: ...


class RoleRepository(Protocol):
    def get_by_id(self, role_id: UUID) -> Role | None: ...

    def get_by_organization_and_slug(
        self,
        organization_id: UUID,
        slug: str,
    ) -> Role | None: ...

    def list_by_organization_id(self, organization_id: UUID) -> list[Role]: ...

    def create(self, role: Role) -> Role: ...

    def update(self, role: Role) -> Role: ...

    def soft_delete(self, role_id: UUID) -> None: ...


class PermissionRepository(Protocol):
    def get_by_id(self, permission_id: UUID) -> Permission | None: ...

    def get_by_code(self, code: str) -> Permission | None: ...

    def list_all(self) -> list[Permission]: ...

    def create(self, permission: Permission) -> Permission: ...


class RolePermissionRepository(Protocol):
    def grant(self, role_permission: RolePermission) -> None: ...

    def revoke(self, role_id: UUID, permission_id: UUID) -> None: ...

    def list_permission_ids_for_role(self, role_id: UUID) -> list[UUID]: ...

    def has_permission(self, role_id: UUID, permission_id: UUID) -> bool: ...


class PermissionChecker(Protocol):
    def has_permission(
        self,
        user_id: UUID,
        organization_id: UUID,
        permission_code: str,
    ) -> bool: ...


class SessionRepository(Protocol):
    def create(self, session: Session) -> Session: ...

    def get_by_id(self, session_id: UUID) -> Session | None: ...

    def update(self, session: Session) -> Session: ...

    def revoke(self, session_id: UUID, revoked_at: datetime) -> None: ...


class RefreshTokenRepository(Protocol):
    def create(self, refresh_token: RefreshToken) -> RefreshToken: ...

    def get_by_token_hash(self, token_hash: str) -> RefreshToken | None: ...

    def revoke(self, refresh_token_id: UUID, revoked_at: datetime) -> None: ...
