from fastapi import APIRouter

from app.api.v1 import health
from app.modules.identity.api.authentication.routes import router as identity_auth_router

api_v1_router = APIRouter()
api_v1_router.include_router(health.router, tags=["health"])
api_v1_router.include_router(identity_auth_router)
