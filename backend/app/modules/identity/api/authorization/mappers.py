from app.modules.identity.application.authorization.results import AuthorizationDecision
from app.modules.identity.api.authorization.schemas import CheckPermissionResponse


def authorization_decision_to_response(decision: AuthorizationDecision) -> CheckPermissionResponse:
    return CheckPermissionResponse(
        allowed=decision.allowed,
        permission_code=decision.permission_code.value,
    )
