from app.core.exceptions import AppException
from app.modules.settings.domain.exceptions import (
    InvalidSettingKeyError,
    InvalidSettingScopeError,
    InvalidSettingValueError,
    SettingError,
    SettingNotFoundError,
)


def map_setting_error(exc: SettingError) -> AppException:
    if isinstance(exc, SettingNotFoundError):
        return AppException(str(exc), status_code=404)
    if isinstance(
        exc,
        (InvalidSettingKeyError, InvalidSettingValueError, InvalidSettingScopeError),
    ):
        return AppException(str(exc), status_code=400)
    return AppException(str(exc), status_code=400)
