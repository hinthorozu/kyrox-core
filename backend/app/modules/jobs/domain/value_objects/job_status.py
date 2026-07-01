from enum import StrEnum


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

    def can_transition_to(self, next_status: "JobStatus") -> bool:
        allowed: dict[JobStatus, frozenset[JobStatus]] = {
            JobStatus.PENDING: frozenset({JobStatus.RUNNING}),
            JobStatus.RUNNING: frozenset(
                {JobStatus.COMPLETED, JobStatus.PENDING, JobStatus.FAILED}
            ),
            JobStatus.COMPLETED: frozenset(),
            JobStatus.FAILED: frozenset(),
        }
        return next_status in allowed[self]
