from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.config import settings
from app.modules.jobs.application.worker.fair_crm_lifecycle_handler import (
    FairCrmSuspensionSecuritySignalHandler,
)
from app.modules.jobs.domain.entities import Job
from app.modules.jobs.domain.value_objects.job_status import JobStatus
from app.modules.jobs.domain.value_objects.job_type import JobType


def _job() -> Job:
    organization_id = uuid4()
    episode = "2026-09-09T16:00:00.123456"
    return Job(
        id=uuid4(),
        organization_id=organization_id,
        job_type=JobType.create("core.identity.organization_suspended"),
        payload={
            "organization_id": str(organization_id),
            "lifecycle_updated_at": episode,
        },
        status=JobStatus.RUNNING,
        idempotency_key="organization-suspended-test",
        attempt_count=1,
        max_attempts=10,
        result=None,
        failure_reason=None,
        created_at=datetime.now(UTC),
        started_at=datetime.now(UTC),
        finished_at=None,
    )


def test_handler_delivers_purpose_separated_signal(monkeypatch: pytest.MonkeyPatch) -> None:
    job = _job()
    captured: dict[str, object] = {}

    class CapturingClient:
        def __init__(self, *, timeout: float) -> None:
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            _ = (exc_type, exc, tb)

        def post(self, url: str, *, headers: dict[str, str], json: dict[str, str]):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return SimpleNamespace(status_code=200)

    monkeypatch.setattr(settings, "FAIR_CRM_BASE_URL", "http://fair.example/")
    monkeypatch.setattr(
        settings,
        "FAIR_CRM_CORE_LIFECYCLE_SIGNAL_TOKEN",
        "signal-secret",
    )
    monkeypatch.setattr(
        "app.modules.jobs.application.worker.fair_crm_lifecycle_handler.httpx.Client",
        CapturingClient,
    )

    result = FairCrmSuspensionSecuritySignalHandler().handle(job)

    assert captured["url"] == (
        "http://fair.example/api/v1/internal/lifecycle-security/organization-suspended"
    )
    assert captured["headers"] == {
        "X-Kyrox-Lifecycle-Signal-Token": "signal-secret",
        "Accept": "application/json",
    }
    assert captured["json"] == job.payload
    assert captured["timeout"] == 10.0
    assert result.result == {
        "delivered": True,
        "organization_id": job.payload["organization_id"],
        "lifecycle_updated_at": job.payload["lifecycle_updated_at"],
    }


def test_handler_fails_closed_when_signal_token_is_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "FAIR_CRM_CORE_LIFECYCLE_SIGNAL_TOKEN", None)

    with pytest.raises(RuntimeError, match="not configured"):
        FairCrmSuspensionSecuritySignalHandler().handle(_job())


def test_handler_keeps_non_200_delivery_retryable_via_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingClient:
        def __init__(self, *, timeout: float) -> None:
            _ = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            _ = (exc_type, exc, tb)

        def post(self, url: str, *, headers: dict[str, str], json: dict[str, str]):
            _ = (url, headers, json)
            return SimpleNamespace(status_code=503)

    monkeypatch.setattr(
        settings,
        "FAIR_CRM_CORE_LIFECYCLE_SIGNAL_TOKEN",
        "signal-secret",
    )
    monkeypatch.setattr(
        "app.modules.jobs.application.worker.fair_crm_lifecycle_handler.httpx.Client",
        FailingClient,
    )

    with pytest.raises(RuntimeError, match="status=503"):
        FairCrmSuspensionSecuritySignalHandler().handle(_job())
