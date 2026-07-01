from pydantic import BaseModel, Field


class CheckPermissionRequest(BaseModel):
    permission_code: str = Field(..., min_length=1, max_length=255)


class CheckPermissionResponse(BaseModel):
    allowed: bool
    permission_code: str


class ErrorResponse(BaseModel):
    detail: str
