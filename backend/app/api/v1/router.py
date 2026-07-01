from fastapi import APIRouter

from app.api.v1 import health
from app.modules.audit.api.routes import router as audit_router
from app.modules.jobs.api.routes import router as jobs_router
from app.modules.notifications.api.routes import router as notifications_router
from app.modules.settings.api.routes import router as settings_router
from app.modules.identity.api.authentication.routes import router as identity_auth_router
from app.modules.identity.api.authorization.routes import router as identity_authorization_router
from app.modules.identity.api.membership.routes import router as identity_membership_router
from app.modules.identity.api.organization.routes import router as identity_organization_router

api_v1_router = APIRouter()
api_v1_router.include_router(health.router, tags=["health"])
api_v1_router.include_router(identity_auth_router)
api_v1_router.include_router(identity_organization_router)
api_v1_router.include_router(identity_membership_router)
api_v1_router.include_router(identity_authorization_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(settings_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(notifications_router)
