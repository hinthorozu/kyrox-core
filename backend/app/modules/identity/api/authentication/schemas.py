from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class PublicSignupRequest(BaseModel):
    organization_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    organization_slug: str | None = Field(default=None, min_length=2, max_length=255)


class PublicSignupResponse(BaseModel):
    message: str


class CompleteActivationRequest(BaseModel):
    token: str = Field(min_length=1)
    password: str = Field(min_length=1, max_length=255)


class CompleteActivationResponse(BaseModel):
    message: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class ErrorResponse(BaseModel):
    detail: str
