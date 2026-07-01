class SettingError(Exception):
    """Base exception for settings domain errors."""


class SettingNotFoundError(SettingError):
    """Raised when a setting does not exist for the given scope and key."""


class InvalidSettingKeyError(SettingError):
    """Raised when a setting key violates format rules."""


class InvalidSettingValueError(SettingError):
    """Raised when a setting value violates JSON or size rules."""


class InvalidSettingScopeError(SettingError):
    """Raised when scope and organization_id are inconsistent."""
