import pytest

from app.modules.jobs.domain.exceptions import InvalidJobTypeError
from app.modules.jobs.domain.value_objects.job_status import JobStatus
from app.modules.jobs.domain.value_objects.job_type import JobType


def test_job_type_accepts_valid_namespaced_type() -> None:
    job_type = JobType.create("core.platform.echo")
    assert job_type.value == "core.platform.echo"


def test_job_status_transition_rules() -> None:
    assert JobStatus.PENDING.can_transition_to(JobStatus.RUNNING) is True
    assert JobStatus.RUNNING.can_transition_to(JobStatus.COMPLETED) is True
    assert JobStatus.RUNNING.can_transition_to(JobStatus.PENDING) is True
    assert JobStatus.RUNNING.can_transition_to(JobStatus.FAILED) is True
    assert JobStatus.COMPLETED.can_transition_to(JobStatus.PENDING) is False
    assert JobStatus.FAILED.can_transition_to(JobStatus.RUNNING) is False


def test_job_type_rejects_invalid_format() -> None:
    with pytest.raises(InvalidJobTypeError):
        JobType.create("invalid")
