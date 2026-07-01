from dataclasses import dataclass

from app.modules.identity.application.authentication.commands import ClientContextCommand
from app.modules.identity.domain.authentication.value_objects.client.client_fingerprint import (
    ClientFingerprint,
)
from app.modules.identity.domain.authentication.value_objects.client.device_name import DeviceName
from app.modules.identity.domain.authentication.value_objects.client.ip_address import IpAddress
from app.modules.identity.domain.authentication.value_objects.client.user_agent import UserAgent


@dataclass(frozen=True, slots=True)
class ParsedClientContext:
    ip_address: IpAddress | None = None
    user_agent: UserAgent | None = None
    device_name: DeviceName | None = None
    client_fingerprint: ClientFingerprint | None = None


def _parse_optional(value: str | None, factory: type) -> object | None:
    if value is None or not value.strip():
        return None
    try:
        return factory.create(value)
    except ValueError:
        # TODO: emit audit event for invalid client context field when audit is available
        return None


def parse_client_context(command: ClientContextCommand | None) -> ParsedClientContext:
    if command is None:
        return ParsedClientContext()

    return ParsedClientContext(
        ip_address=_parse_optional(command.ip_address, IpAddress),
        user_agent=_parse_optional(command.user_agent, UserAgent),
        device_name=_parse_optional(command.device_name, DeviceName),
        client_fingerprint=_parse_optional(command.client_fingerprint, ClientFingerprint),
    )
