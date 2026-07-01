from dataclasses import dataclass


_MAX_CLIENT_FINGERPRINT_LENGTH = 256


@dataclass(frozen=True, slots=True)
class ClientFingerprint:
    value: str

    @classmethod
    def create(cls, raw: str) -> "ClientFingerprint":
        normalized = raw.strip()
        if not normalized:
            raise ValueError("Client fingerprint cannot be empty")
        if len(normalized) > _MAX_CLIENT_FINGERPRINT_LENGTH:
            raise ValueError("Client fingerprint exceeds maximum length")
        return cls(value=normalized)

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("Client fingerprint cannot be empty")
        if len(self.value) > _MAX_CLIENT_FINGERPRINT_LENGTH:
            raise ValueError("Client fingerprint exceeds maximum length")
