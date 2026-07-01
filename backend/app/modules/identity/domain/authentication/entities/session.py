from dataclasses import dataclass
from datetime import datetime

from app.modules.identity.domain.authentication.exceptions import AuthenticationError
from app.modules.identity.domain.authentication.value_objects.client.client_fingerprint import (
    ClientFingerprint,
)
from app.modules.identity.domain.authentication.value_objects.client.device_name import DeviceName
from app.modules.identity.domain.authentication.value_objects.client.ip_address import IpAddress
from app.modules.identity.domain.authentication.value_objects.client.user_agent import UserAgent
from app.modules.identity.domain.authentication.value_objects.identity.session_id import SessionId
from app.modules.identity.domain.authentication.value_objects.identity.user_id import UserId


@dataclass
class Session:
    id: SessionId
    user_id: UserId
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime | None = None
    revoked_at: datetime | None = None
    ip_address: IpAddress | None = None
    user_agent: UserAgent | None = None
    device_name: DeviceName | None = None
    client_fingerprint: ClientFingerprint | None = None

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    def revoke(self, at: datetime) -> None:
        self.revoked_at = at
        self.updated_at = at

    def record_activity(self, at: datetime) -> None:
        self.last_activity_at = at
        self.updated_at = at

    def assert_active(self) -> None:
        if not self.is_active:
            raise AuthenticationError("Session is no longer active")
