from dataclasses import dataclass

_MAX_LENGTH = 255


@dataclass(frozen=True, slots=True)
class OrganizationName:
    value: str

    @classmethod
    def create(cls, raw: str) -> "OrganizationName":
        normalized = raw.strip()
        if not normalized:
            raise ValueError("Organization name cannot be empty")
        if len(normalized) > _MAX_LENGTH:
            raise ValueError("Organization name is too long")
        return cls(value=normalized)

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("Organization name cannot be empty")
