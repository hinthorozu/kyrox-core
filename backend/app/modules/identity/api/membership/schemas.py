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


class ErrorResponse(BaseModel):
    detail: str
