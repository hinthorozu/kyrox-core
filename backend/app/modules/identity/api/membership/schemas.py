from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.modules.identity.domain.membership.enums.membership_status import MembershipStatus


class InviteMemberRequest(BaseModel):
    email: EmailStr


class InviteMemberResponse(BaseModel):
    invite_id: UUID
    token: str
    expires_at: datetime


class AcceptMembershipInviteRequest(BaseModel):
    token: str = Field(min_length=1)


class RegisterMembershipInviteRequest(BaseModel):
    token: str = Field(min_length=1)
    password: str = Field(min_length=8)


class CreateOrganizationUserRequest(BaseModel):
    email: EmailStr
    temporary_password: str = Field(min_length=8)
    role_slug: str | None = Field(default=None, min_length=1)


class MembershipResponse(BaseModel):
    id: UUID
    user_id: UUID
    organization_id: UUID
    status: MembershipStatus
    joined_at: datetime | None


class MembershipListResponse(BaseModel):
    memberships: list[MembershipResponse]


class AcceptMembershipInviteResponse(BaseModel):
    membership: MembershipResponse
    organization_id: UUID


class CreateOrganizationUserResponse(BaseModel):
    user_id: UUID
    email: EmailStr
    must_change_password: bool
    membership: MembershipResponse


class ErrorResponse(BaseModel):
    detail: str
