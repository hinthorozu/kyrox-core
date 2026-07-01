import uuid

from sqlalchemy.orm import Session

from app.modules.jobs.application.commands import EnqueueJobCommand, ProcessPendingJobsCommand
from app.modules.jobs.application.enqueue_job import EnqueueJobUseCase
from app.modules.jobs.application.process_pending_jobs import ProcessPendingJobsUseCase
from app.modules.jobs.bootstrap import build_job_handler_registry
from app.modules.jobs.infrastructure.repositories import SqlAlchemyJobRepository


def test_repository_claim_next_pending_completes_echo_job(db_session: Session) -> None:
    repository = SqlAlchemyJobRepository(db_session)
    registry = build_job_handler_registry()
    org_id = uuid.uuid4()

    result = EnqueueJobUseCase(repository).execute(
        EnqueueJobCommand(
            organization_id=org_id,
            job_type="core.platform.echo",
            payload={"message": "hello"},
        )
    )
    db_session.commit()

    use_case = ProcessPendingJobsUseCase(repository, registry)
    processed = use_case.execute(ProcessPendingJobsCommand(limit=10))
    db_session.commit()

    assert processed == 1
    saved = repository.get_by_id(result.job.id)
    assert saved is not None
    assert saved.status.value == "completed"
    assert saved.result == {"echo": {"message": "hello"}}


def test_claim_pending_sqlite_is_transaction_safe(db_session: Session) -> None:
    repository = SqlAlchemyJobRepository(db_session)
    org_id = uuid.uuid4()
    result = EnqueueJobUseCase(repository).execute(
        EnqueueJobCommand(
            organization_id=org_id,
            job_type="core.platform.echo",
            payload={"value": 1},
        )
    )
    db_session.commit()

    claimed = repository.claim_pending(result.job.id)
    assert claimed is not None
    assert claimed.status.value == "running"
    assert claimed.attempt_count == 1

    second_claim = repository.claim_pending(result.job.id)
    assert second_claim is None
