from uuid import UUID

from pydantic import BaseModel, Field


class PermissionResponse(BaseModel):
    id: UUID
    code: str
    description: str
    lifecycle_state: str
    is_assignable: bool
    permission_scope: str


class RoleResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    role_kind: str
    organization_id: UUID | None
    source_template_role_id: UUID | None
    template_version: int
    source_template_version: int | None
    permissions_customized: bool
    is_assignable: bool
    is_protected: bool
    permission_ids: list[UUID]


class RoleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$", max_length=255)
    permission_ids: list[UUID] = Field(default_factory=list)


class RoleUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9_-]*$", max_length=255)


class RolePermissionsRequest(BaseModel):
    permission_ids: list[UUID]


class DeriveRoleRequest(BaseModel):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$", max_length=255)


class TemplateSyncRequest(BaseModel):
    role_ids: list[UUID] = Field(default_factory=list)
    organization_id: UUID | None = None


class TemplateSyncPreviewResponse(BaseModel):
    role_id: UUID
    role_name: str
    organization_id: UUID
    current_version: int | None
    target_version: int
    add_count: int
    remove_count: int


class PermissionLifecycleRequest(BaseModel):
    state: str = Field(pattern=r"^(active|locked|inactive)$")
    reason: str | None = Field(default=None, max_length=512)


class PermissionLifecyclePreviewResponse(BaseModel):
    permission_id: UUID
    target_state: str
    affected_roles: int
    affected_users: int
