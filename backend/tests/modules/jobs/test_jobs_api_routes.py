import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "identity"))
from identity_api_test_helpers import login

from app.modules.jobs.domain.entities import Job
from app.modules.jobs.domain.value_objects.job_status import JobStatus
from app.modules.jobs.domain.value_objects.job_type import JobType
from app.modules.jobs.infrastructure.repositories import SqlAlchemyJobRepository
from jobs_test_helpers import seed_user_with_job_permissions


def test_enqueue_job_runs_echo_handler(
    client: TestClient,
    db_session: Session,
) -> None:
    user, org = seed_user_with_job_permissions(db_session)
    token = login(client, user.email)

    response = client.post(
        f"/api/v1/organizations/{org.id.value}/jobs",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(org.id.value),
        },
        json={
            "job_type": "core.platform.echo",
            "payload": {"message": "hello"},
        },
    )

    assert response.status_code == 201, response.text
    job_id = response.json()["job"]["id"]

    get_response = client.get(
        f"/api/v1/jobs/{job_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(org.id.value),
        },
    )

    assert get_response.status_code == 200, get_response.text
    body = get_response.json()
    assert body["status"] == "completed"
    assert body["result"] == {"echo": {"message": "hello"}}


def test_get_job_masks_other_organization(
    client: TestClient,
    db_session: Session,
) -> None:
    user, org = seed_user_with_job_permissions(db_session)
    other_org_id = uuid.uuid4()
    repository = SqlAlchemyJobRepository(db_session)
    job_id = uuid.uuid4()
    now = datetime.now(UTC)
    repository.save(
        Job(
            id=job_id,
            organization_id=other_org_id,
            job_type=JobType.create("core.platform.echo"),
            payload={"message": "secret"},
            status=JobStatus.COMPLETED,
            idempotency_key=None,
            attempt_count=1,
            max_attempts=3,
            result={"echo": {"message": "secret"}},
            failure_reason=None,
            created_at=now,
            started_at=now,
            finished_at=now,
        )
    )
    db_session.commit()
    token = login(client, user.email)

    get_response = client.get(
        f"/api/v1/jobs/{job_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(org.id.value),
        },
    )

    assert get_response.status_code == 404


def test_enqueue_job_idempotency_returns_existing_job(
    client: TestClient,
    db_session: Session,
) -> None:
    user, org = seed_user_with_job_permissions(db_session)
    token = login(client, user.email)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": str(org.id.value),
    }
    body = {
        "job_type": "core.platform.echo",
        "payload": {"message": "hello"},
        "idempotency_key": "export-1",
    }

    first = client.post(f"/api/v1/organizations/{org.id.value}/jobs", headers=headers, json=body)
    second = client.post(f"/api/v1/organizations/{org.id.value}/jobs", headers=headers, json=body)

    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert first.json()["job"]["id"] == second.json()["job"]["id"]
    assert second.json()["created"] is False
