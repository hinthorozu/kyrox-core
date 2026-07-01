from dataclasses import dataclass


_MAX_IP_LENGTH = 45


@dataclass(frozen=True, slots=True)
class IpAddress:
    value: str

    @classmethod
    def create(cls, raw: str) -> "IpAddress":
        normalized = raw.strip()
        if not normalized:
            raise ValueError("IP address cannot be empty")
        if len(normalized) > _MAX_IP_LENGTH:
            raise ValueError("IP address exceeds maximum length")
        return cls(value=normalized)

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("IP address cannot be empty")
        if len(self.value) > _MAX_IP_LENGTH:
            raise ValueError("IP address exceeds maximum length")
