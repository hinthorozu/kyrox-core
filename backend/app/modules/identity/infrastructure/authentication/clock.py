from datetime import UTC, datetime

from app.modules.identity.domain.authentication.ports.clock import Clock


class UtcClock:
    def now(self) -> datetime:
        return datetime.now(tz=UTC)
