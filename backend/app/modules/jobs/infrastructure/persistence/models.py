from datetime import datetime
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, Index, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime, UUIDPrimaryKey
from app.db.utils import generate_uuid


class PlatformJobModel(Base):
    __tablename__ = "platform_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_platform_jobs_status",
        ),
        CheckConstraint("attempt_count >= 0", name="ck_platform_jobs_attempt_count"),
        CheckConstraint("max_attempts >= 1", name="ck_platform_jobs_max_attempts"),
        CheckConstraint(
            "attempt_count <= max_attempts",
            name="ck_platform_jobs_attempt_lte_max",
        ),
        Index("ix_platform_jobs_organization_id", "organization_id"),
        Index("ix_platform_jobs_status_created", "status", "created_at"),
        Index(
            "uq_platform_jobs_org_type_idempotency",
            "organization_id",
            "job_type",
            "idempotency_key",
            unique=True,
            postgresql_where=sa.text("idempotency_key IS NOT NULL"),
            sqlite_where=sa.text("idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDPrimaryKey,
        primary_key=True,
        default=generate_uuid,
    )
    organization_id: Mapped[UUID] = mapped_column(UUIDPrimaryKey, nullable=False)
    job_type: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attempt_count: Mapped[int] = mapped_column(nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(nullable=False, default=3)
    result: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
