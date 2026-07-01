from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime, UUIDPrimaryKey
from app.db.utils import generate_uuid


class AuditLogModel(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_organization_id", "organization_id"),
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_session_id", "session_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_resource_type", "resource_type"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDPrimaryKey,
        primary_key=True,
        default=generate_uuid,
    )
    organization_id: Mapped[UUID | None] = mapped_column(UUIDPrimaryKey, nullable=True)
    user_id: Mapped[UUID | None] = mapped_column(UUIDPrimaryKey, nullable=True)
    session_id: Mapped[UUID | None] = mapped_column(UUIDPrimaryKey, nullable=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    old_values: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    new_values: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        server_default=func.now(),
    )
