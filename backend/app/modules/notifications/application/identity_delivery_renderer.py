from urllib.parse import quote
from uuid import UUID

from app.modules.identity.application.authentication.identity_action_tokens import (
    MaterializeIdentityActionToken,
)
from app.modules.identity.domain.authentication.enums.identity_action_token_purpose import (
    IdentityActionTokenPurpose,
)
from app.modules.identity.domain.authentication.value_objects.identity.identity_action_token_id import (
    IdentityActionTokenId,
)
from app.modules.notifications.application.identity_templates import (
    IDENTITY_ACTIVATION_TEMPLATE_KEY,
    IDENTITY_PASSWORD_RESET_TEMPLATE_KEY,
    build_activation_email,
    build_password_reset_email,
)
from app.modules.notifications.application.ports.content_renderer import RenderedNotificationContent
from app.modules.notifications.domain.entities import Notification

_TOKEN_ID_VARIABLE = "identity_action_token_id"


class IdentityNotificationContentRenderer:
    def __init__(
        self,
        *,
        materialize_identity_action_token: MaterializeIdentityActionToken,
        activation_url_template: str,
        password_reset_url_template: str,
    ) -> None:
        self._materialize_identity_action_token = materialize_identity_action_token
        self._activation_url_template = activation_url_template
        self._password_reset_url_template = password_reset_url_template

    def render(self, notification: Notification) -> RenderedNotificationContent:
        if notification.template_key == IDENTITY_ACTIVATION_TEMPLATE_KEY:
            action_url = self._action_url(
                notification,
                purpose=IdentityActionTokenPurpose.ACCOUNT_ACTIVATION,
                url_template=self._activation_url_template,
            )
            rendered = build_activation_email(action_url=action_url)
            return RenderedNotificationContent(subject=rendered.subject, body=rendered.body)

        if notification.template_key == IDENTITY_PASSWORD_RESET_TEMPLATE_KEY:
            action_url = self._action_url(
                notification,
                purpose=IdentityActionTokenPurpose.PASSWORD_RESET,
                url_template=self._password_reset_url_template,
            )
            rendered = build_password_reset_email(action_url=action_url)
            return RenderedNotificationContent(subject=rendered.subject, body=rendered.body)

        return RenderedNotificationContent(
            subject=notification.subject,
            body=notification.body,
        )

    def _action_url(
        self,
        notification: Notification,
        *,
        purpose: IdentityActionTokenPurpose,
        url_template: str,
    ) -> str:
        variables = notification.variables or {}
        raw_token_id = variables.get(_TOKEN_ID_VARIABLE)
        if raw_token_id is None:
            raise ValueError("Identity action token reference is missing")
        try:
            token_id = IdentityActionTokenId(UUID(str(raw_token_id)))
        except ValueError as exc:
            raise ValueError("Identity action token reference is invalid") from exc

        raw_token = self._materialize_identity_action_token.execute(token_id, purpose)
        if "{token}" not in url_template:
            raise ValueError("Identity action URL template must contain {token}")
        return url_template.replace("{token}", quote(raw_token, safe=""))
