from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.identity.domain.organization.enums.organization_status import OrganizationStatus


class CreateOrganizationRequest(BaseModel):
    name: str = Field(min_length=1)
    slug: str = Field(min_length=1)


class UpdateOrganizationRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    status: OrganizationStatus
    created_at: datetime
    updated_at: datetime


class CreateOrganizationResponse(BaseModel):
    organization: OrganizationResponse
    membership_id: UUID


class ErrorResponse(BaseModel):
    detail: str
