from typing import Protocol
from uuid import UUID, uuid4


class IdGenerator(Protocol):
    def generate_uuid(self) -> UUID: ...


class Uuid4IdGenerator:
    def generate_uuid(self) -> UUID:
        return uuid4()
