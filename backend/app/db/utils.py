import uuid
from datetime import UTC, datetime


def generate_uuid() -> uuid.UUID:
    """Generate a primary-key UUID.

    Uses UUIDv7 on Python 3.14+ for time-ordered identifiers.
    Falls back to UUID4 on older runtimes.
    TODO(ADR): require UUIDv7 once minimum Python is 3.14+.
    """
    uuid7 = getattr(uuid, "uuid7", None)
    if uuid7 is not None:
        return uuid7()
    return uuid.uuid4()


def utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)
