import re
from dataclasses import dataclass

from app.modules.jobs.domain.exceptions import InvalidJobTypeError

_JOB_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2,}$")
_MAX_JOB_TYPE_LENGTH = 255


@dataclass(frozen=True, slots=True)
class JobType:
    value: str

    @classmethod
    def create(cls, raw: str) -> "JobType":
        normalized = raw.strip().lower()
        if not normalized:
            raise InvalidJobTypeError("Job type cannot be empty")
        if len(normalized) > _MAX_JOB_TYPE_LENGTH:
            raise InvalidJobTypeError(
                f"Job type exceeds maximum length of {_MAX_JOB_TYPE_LENGTH} characters"
            )
        if not _JOB_TYPE_PATTERN.match(normalized):
            raise InvalidJobTypeError(
                "Job type must be lowercase dot-separated with at least three segments"
            )
        return cls(value=normalized)
