from enum import StrEnum


class IdentityActionTokenPurpose(StrEnum):
    ACCOUNT_ACTIVATION = "account_activation"
    PASSWORD_RESET = "password_reset"
