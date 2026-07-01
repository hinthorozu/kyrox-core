from dataclasses import dataclass

from app.modules.jobs.domain.exceptions import InvalidJobPayloadError

_MAX_MESSAGE_LENGTH = 2048
_MAX_CODE_LENGTH = 64


@dataclass(frozen=True, slots=True)
class FailureReason:
    message: str
    code: str | None = None

    @classmethod
    def create(cls, message: str, code: str | None = None) -> "FailureReason":
        normalized_message = message.strip()
        if not normalized_message:
            raise InvalidJobPayloadError("Failure reason message cannot be empty")
        if len(normalized_message) > _MAX_MESSAGE_LENGTH:
            raise InvalidJobPayloadError(
                f"Failure reason exceeds maximum length of {_MAX_MESSAGE_LENGTH} characters"
            )
        normalized_code = None
        if code is not None:
            normalized_code = code.strip()
            if not normalized_code:
                raise InvalidJobPayloadError("Failure code cannot be empty")
            if len(normalized_code) > _MAX_CODE_LENGTH:
                raise InvalidJobPayloadError(
                    f"Failure code exceeds maximum length of {_MAX_CODE_LENGTH} characters"
                )
        return cls(message=normalized_message, code=normalized_code)
