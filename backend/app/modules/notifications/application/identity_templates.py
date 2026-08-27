from dataclasses import dataclass


IDENTITY_ACTIVATION_TEMPLATE_KEY = "identity.account_activation"
IDENTITY_PASSWORD_RESET_TEMPLATE_KEY = "identity.password_reset"
IDENTITY_PASSWORD_CHANGED_TEMPLATE_KEY = "identity.password_changed"


@dataclass(frozen=True, slots=True)
class IdentityEmailTemplate:
    template_key: str
    subject: str
    body: str


def build_activation_email(*, action_url: str) -> IdentityEmailTemplate:
    return IdentityEmailTemplate(
        template_key=IDENTITY_ACTIVATION_TEMPLATE_KEY,
        subject="Activate your KYROX account",
        body=(
            "Activate your KYROX account using the secure link below.\n\n"
            f"{_required_action_url(action_url)}\n\n"
            "If you did not request this account, you can ignore this message."
        ),
    )


def build_password_reset_email(*, action_url: str) -> IdentityEmailTemplate:
    return IdentityEmailTemplate(
        template_key=IDENTITY_PASSWORD_RESET_TEMPLATE_KEY,
        subject="Reset your KYROX password",
        body=(
            "Reset your KYROX password using the secure link below.\n\n"
            f"{_required_action_url(action_url)}\n\n"
            "If you did not request a password reset, you can ignore this message."
        ),
    )


def build_password_changed_email() -> IdentityEmailTemplate:
    return IdentityEmailTemplate(
        template_key=IDENTITY_PASSWORD_CHANGED_TEMPLATE_KEY,
        subject="Your KYROX password was changed",
        body=(
            "Your KYROX account password was changed.\n\n"
            "If you did not make this change, contact your administrator or support immediately."
        ),
    )


def _required_action_url(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Identity action URL is required")
    if "\n" in normalized or "\r" in normalized:
        raise ValueError("Identity action URL must be a single line")
    return normalized
