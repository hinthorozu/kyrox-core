import logging
import smtplib
from email.message import EmailMessage

from app.modules.notifications.domain.exceptions import NotificationDispatchError
from app.modules.notifications.domain.ports import (
    ChannelDispatchRequest,
    ChannelDispatchResult,
    NotificationChannelAdapter,
)
from app.modules.notifications.infrastructure.channels.email_log_stub_adapter import redact_recipient

logger = logging.getLogger(__name__)


class SmtpEmailAdapter(NotificationChannelAdapter):
    def __init__(
        self,
        *,
        host: str,
        port: int,
        default_from_address: str,
        username: str | None = None,
        password: str | None = None,
        starttls: bool = True,
        use_ssl: bool = False,
        timeout_seconds: float = 10.0,
    ) -> None:
        normalized_host = host.strip()
        normalized_from = default_from_address.strip()
        if not normalized_host:
            raise ValueError("Core SMTP host is required")
        if not normalized_from:
            raise ValueError("Core email from address is required")
        if port < 1 or port > 65535:
            raise ValueError("Core SMTP port must be between 1 and 65535")
        if timeout_seconds <= 0:
            raise ValueError("Core SMTP timeout must be positive")
        if starttls and use_ssl:
            raise ValueError("Core SMTP STARTTLS and SSL cannot both be enabled")
        if bool(username) != bool(password):
            raise ValueError("Core SMTP username and password must be configured together")

        self._host = normalized_host
        self._port = port
        self._default_from_address = normalized_from
        self._username = username
        self._password = password
        self._starttls = starttls
        self._use_ssl = use_ssl
        self._timeout_seconds = timeout_seconds

    def send(self, request: ChannelDispatchRequest) -> ChannelDispatchResult:
        from_address = (request.from_address or self._default_from_address).strip()
        if not from_address:
            raise NotificationDispatchError("Core email sender is not configured")

        message = EmailMessage()
        message["From"] = from_address
        message["To"] = request.recipient.value
        message["Subject"] = request.subject
        message.set_content(request.body)

        try:
            if self._use_ssl:
                client: smtplib.SMTP = smtplib.SMTP_SSL(
                    self._host,
                    self._port,
                    timeout=self._timeout_seconds,
                )
            else:
                client = smtplib.SMTP(
                    self._host,
                    self._port,
                    timeout=self._timeout_seconds,
                )
            with client:
                if self._starttls:
                    client.starttls()
                if self._username is not None and self._password is not None:
                    client.login(self._username, self._password)
                refused = client.send_message(message)
                if refused:
                    raise NotificationDispatchError("Core email provider refused recipient")
        except NotificationDispatchError:
            raise
        except (OSError, smtplib.SMTPException) as exc:
            # Do not propagate provider responses: they may contain message fragments,
            # recipients or other sensitive identity-mail material.
            raise NotificationDispatchError("Core email provider dispatch failed") from exc

        logger.info(
            "notification email smtp dispatch",
            extra={
                "notification_id": str(request.notification_id),
                "organization_id": (
                    str(request.organization_id) if request.organization_id is not None else None
                ),
                "channel": request.channel.value,
                "recipient_redacted": redact_recipient(request.recipient.value),
                "template_key": request.template_key,
            },
        )
        return ChannelDispatchResult(provider_message_id=None)
