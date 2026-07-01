from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session as DbSession

from app.modules.jobs.domain.entities import Job
from app.modules.jobs.domain.value_objects.job_status import JobStatus
from app.modules.jobs.domain.value_objects.job_type import JobType
from app.modules.jobs.infrastructure.persistence.mappers import (
    apply_job_to_model,
    job_to_domain,
    job_to_model,
)
from app.modules.jobs.infrastructure.persistence.models import PlatformJobModel


class SqlAlchemyJobRepository:
    def __init__(self, session: DbSession) -> None:
        self._session = session

    def get_by_id(self, job_id: UUID) -> Job | None:
        model = self._session.get(PlatformJobModel, job_id)
        if model is None:
            return None
        return job_to_domain(model)

    def find_by_idempotency(
        self,
        organization_id: UUID,
        job_type: JobType,
        idempotency_key: str,
    ) -> Job | None:
        stmt = select(PlatformJobModel).where(
            PlatformJobModel.organization_id == organization_id,
            PlatformJobModel.job_type == job_type.value,
            PlatformJobModel.idempotency_key == idempotency_key,
        )
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        return job_to_domain(model)

    def save(self, job: Job) -> Job:
        model = self._session.get(PlatformJobModel, job.id)
        if model is None:
            model = job_to_model(job)
            self._session.add(model)
        else:
            apply_job_to_model(job, model)
            model.updated_at = datetime.now(UTC)
        self._session.flush()
        return job_to_domain(model)

    def list_pending(self, *, limit: int) -> list[Job]:
        stmt = (
            select(PlatformJobModel)
            .where(PlatformJobModel.status == JobStatus.PENDING.value)
            .order_by(PlatformJobModel.created_at.asc())
            .limit(limit)
        )
        models = self._session.scalars(stmt).all()
        return [job_to_domain(model) for model in models]

    def claim_pending(self, job_id: UUID) -> Job | None:
        if self._uses_postgresql():
            return self._claim_pending_postgresql(job_id)
        return self._claim_pending_sqlite(job_id)

    def claim_next_pending(self, *, limit: int) -> list[Job]:
        if self._uses_postgresql():
            return self._claim_next_pending_postgresql(limit)
        return self._claim_next_pending_sqlite(limit)

    def _uses_postgresql(self) -> bool:
        bind = self._session.get_bind()
        if bind is None:
            return False
        return bind.dialect.name == "postgresql"

    def _claim_next_pending_postgresql(self, limit: int) -> list[Job]:
        pending_ids_stmt = (
            select(PlatformJobModel.id)
            .where(PlatformJobModel.status == JobStatus.PENDING.value)
            .order_by(PlatformJobModel.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        job_ids = list(self._session.scalars(pending_ids_stmt).all())
        claimed: list[Job] = []
        now = datetime.now(UTC)
        for job_id in job_ids:
            model = self._session.get(PlatformJobModel, job_id)
            if model is None or model.status != JobStatus.PENDING.value:
                continue
            model.status = JobStatus.RUNNING.value
            model.started_at = now
            model.attempt_count = model.attempt_count + 1
            model.updated_at = now
            claimed.append(job_to_domain(model))
        if claimed:
            self._session.flush()
        return claimed

    def _claim_next_pending_sqlite(self, limit: int) -> list[Job]:
        pending_jobs = self.list_pending(limit=limit)
        claimed: list[Job] = []
        for pending in pending_jobs:
            claimed_job = self._claim_pending_sqlite(pending.id)
            if claimed_job is not None:
                claimed.append(claimed_job)
        return claimed

    def _claim_pending_postgresql(self, job_id: UUID) -> Job | None:
        stmt = (
            select(PlatformJobModel)
            .where(
                PlatformJobModel.id == job_id,
                PlatformJobModel.status == JobStatus.PENDING.value,
            )
            .with_for_update(skip_locked=True)
        )
        model = self._session.scalars(stmt).first()
        if model is None:
            return None
        now = datetime.now(UTC)
        model.status = JobStatus.RUNNING.value
        model.started_at = now
        model.attempt_count = model.attempt_count + 1
        model.updated_at = now
        self._session.flush()
        return job_to_domain(model)

    def _claim_pending_sqlite(self, job_id: UUID) -> Job | None:
        now = datetime.now(UTC)
        stmt = (
            update(PlatformJobModel)
            .where(
                PlatformJobModel.id == job_id,
                PlatformJobModel.status == JobStatus.PENDING.value,
            )
            .values(
                status=JobStatus.RUNNING.value,
                started_at=now,
                attempt_count=PlatformJobModel.attempt_count + 1,
                updated_at=now,
            )
        )
        result = self._session.execute(stmt)
        if result.rowcount == 0:
            return None
        self._session.flush()
        model = self._session.get(PlatformJobModel, job_id)
        assert model is not None
        return job_to_domain(model)
