from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.identity.domain.authentication.enums.user_status import UserStatus


class ManualUserCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1)
    role_id: UUID
    status: UserStatus = UserStatus.ACTIVE
    is_super_admin: bool = False


class ManualUserUpdateRequest(BaseModel):
    email: str | None = Field(default=None, min_length=3, max_length=320)
    password: str | None = Field(default=None, min_length=1)
    role_id: UUID | None = None
    status: UserStatus | None = None
    is_super_admin: bool | None = None


class AssignableRoleResponse(BaseModel):
    id: UUID
    name: str
    slug: str


class ManagedUserResponse(BaseModel):
    id: UUID
    email: str
    status: UserStatus
    organization_id: UUID
    role: AssignableRoleResponse | None
    created_at: datetime
    updated_at: datetime
    is_super_admin: bool | None = None


class ManagedUserListResponse(BaseModel):
    items: list[ManagedUserResponse]
    can_manage_super_admin: bool


class ErrorResponse(BaseModel):
    detail: str
