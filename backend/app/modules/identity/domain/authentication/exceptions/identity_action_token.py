class IdentityActionTokenError(ValueError):
    """Base error for invalid identity action-token use."""


class IdentityActionTokenNotFoundError(IdentityActionTokenError):
    pass


class IdentityActionTokenExpiredError(IdentityActionTokenError):
    pass


class IdentityActionTokenConsumedError(IdentityActionTokenError):
    pass


class IdentityActionTokenInvalidatedError(IdentityActionTokenError):
    pass


class IdentityActionTokenPurposeMismatchError(IdentityActionTokenError):
    pass
