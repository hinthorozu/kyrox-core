from datetime import timedelta
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.db.session import get_db
from app.modules.audit.application.dto import RecordAuditEventCommand
from app.modules.audit.application.service import AuditService
from app.modules.audit.infrastructure.repositories import SqlAlchemyAuditLogRepository
from app.modules.identity.api.authentication.dependencies import (
    get_clock,
    get_consume_identity_action_token,
    get_identity_action_token_repository,
    get_issue_identity_action_token,
    get_password_hasher,
    get_refresh_token_repository,
    get_session_repository,
    get_user_repository,
)
from app.modules.identity.application.authentication.identity_action_tokens import (
    ConsumeIdentityActionToken,
    IssueIdentityActionToken,
)
from app.modules.identity.application.authentication.password_recovery import (
    ForgotPasswordUseCase,
    PasswordResetAuditPort,
    PasswordResetNotificationPort,
    ResetPasswordUseCase,
)
from app.modules.identity.application.authentication.revoke_all_user_sessions import (
    RevokeAllUserSessionsUseCase,
)
from app.modules.identity.domain.authentication.ports.clock import Clock
from app.modules.identity.domain.authentication.ports.identity_action_token_repository import (
    IdentityActionTokenRepository,
)
from app.modules.identity.domain.authentication.ports.password_hasher import PasswordHasher
from app.modules.identity.domain.authentication.ports.refresh_token_repository import (
    RefreshTokenRepository,
)
from app.modules.identity.domain.authentication.ports.session_repository import SessionRepository
from app.modules.identity.domain.authentication.ports.user_repository import UserRepository
from app.modules.identity.domain.authentication.value_objects.identity.identity_action_token_id import (
    IdentityActionTokenId,
)
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId
from app.modules.identity.infrastructure.organization.repositories.sqlalchemy_organization_repository import (
    SqlAlchemyOrganizationRepository,
)
from app.modules.notifications.api.dependencies import get_send_notification_use_case
from app.modules.notifications.application.commands import SendNotificationCommand
from app.modules.notifications.application.identity_templates import (
    IDENTITY_PASSWORD_RESET_TEMPLATE_KEY,
)
from app.modules.notifications.application.send_notification import SendNotificationUseCase
from app.modules.notifications.domain.value_objects.notification_status import NotificationStatus


class _CorePasswordResetNotificationAdapter(PasswordResetNotificationPort):
    def __init__(self, send_notification_use_case: SendNotificationUseCase) -> None:
        self._send_notification_use_case = send_notification_use_case

    def enqueue_password_reset(
        self,
        *,
        recipient: str,
        user_id: UserId,
        token_id: IdentityActionTokenId,
    ) -> bool:
        result = self._send_notification_use_case.execute(
            SendNotificationCommand(
                organization_id=None,
                channel="email",
                recipient=recipient,
                subject="Reset your KYROX password",
                body=(
                    "A password reset was requested for your KYROX account. "
                    "The secure reset link is generated only at delivery time."
                ),
                template_key=IDENTITY_PASSWORD_RESET_TEMPLATE_KEY,
                variables={"identity_action_token_id": str(token_id.value)},
                idempotency_key=f"identity:password-reset:{token_id.value}",
            )
        )
        return result.status is NotificationStatus.QUEUED


class _CorePasswordResetAuditAdapter(PasswordResetAuditPort):
    def __init__(self, db: DbSession) -> None:
        self._audit_service = AuditService(SqlAlchemyAuditLogRepository(db))

    def record_password_reset(
        self,
        *,
        organization_id: UUID | None,
        user_id: UUID,
        sessions_revoked: int,
        refresh_tokens_revoked: int,
    ) -> None:
        self._audit_service.record(
            RecordAuditEventCommand(
                organization_id=organization_id,
                user_id=user_id,
                session_id=None,
                action="identity.password.reset",
                resource_type="identity_user",
                resource_id=str(user_id),
                new_values={"credential_replaced": True},
                metadata={
                    "source": "public_password_reset",
                    "sessions_revoked": sessions_revoked,
                    "refresh_tokens_revoked": refresh_tokens_revoked,
                },
            )
        )


def get_forgot_password_use_case(
    db: DbSession = Depends(get_db),
    user_repository: UserRepository = Depends(get_user_repository),
    token_repository: IdentityActionTokenRepository = Depends(
        get_identity_action_token_repository
    ),
    issue_identity_action_token: IssueIdentityActionToken = Depends(
        get_issue_identity_action_token
    ),
    send_notification_use_case: SendNotificationUseCase = Depends(
        get_send_notification_use_case
    ),
    clock: Clock = Depends(get_clock),
) -> ForgotPasswordUseCase:
    return ForgotPasswordUseCase(
        user_repository=user_repository,
        organization_repository=SqlAlchemyOrganizationRepository(db, clock),
        identity_action_token_repository=token_repository,
        issue_identity_action_token=issue_identity_action_token,
        notification_port=_CorePasswordResetNotificationAdapter(
            send_notification_use_case
        ),
        clock=clock,
        token_ttl=timedelta(
            minutes=settings.CORE_IDENTITY_PASSWORD_RESET_TTL_MINUTES
        ),
        resend_cooldown=timedelta(
            seconds=settings.CORE_IDENTITY_PASSWORD_RESET_COOLDOWN_SECONDS
        ),
    )


def get_reset_password_use_case(
    db: DbSession = Depends(get_db),
    user_repository: UserRepository = Depends(get_user_repository),
    consume_identity_action_token: ConsumeIdentityActionToken = Depends(
        get_consume_identity_action_token
    ),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    session_repository: SessionRepository = Depends(get_session_repository),
    refresh_token_repository: RefreshTokenRepository = Depends(
        get_refresh_token_repository
    ),
    clock: Clock = Depends(get_clock),
) -> ResetPasswordUseCase:
    return ResetPasswordUseCase(
        consume_identity_action_token=consume_identity_action_token,
        user_repository=user_repository,
        organization_repository=SqlAlchemyOrganizationRepository(db, clock),
        password_hasher=password_hasher,
        revoke_all_user_sessions=RevokeAllUserSessionsUseCase(
            session_repository=session_repository,
            refresh_token_repository=refresh_token_repository,
        ),
        clock=clock,
        audit_port=_CorePasswordResetAuditAdapter(db),
    )
