from dataclasses import dataclass


_MAX_DEVICE_NAME_LENGTH = 128


@dataclass(frozen=True, slots=True)
class DeviceName:
    value: str

    @classmethod
    def create(cls, raw: str) -> "DeviceName":
        normalized = raw.strip()
        if not normalized:
            raise ValueError("Device name cannot be empty")
        if len(normalized) > _MAX_DEVICE_NAME_LENGTH:
            raise ValueError("Device name exceeds maximum length")
        return cls(value=normalized)

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("Device name cannot be empty")
        if len(self.value) > _MAX_DEVICE_NAME_LENGTH:
            raise ValueError("Device name exceeds maximum length")
