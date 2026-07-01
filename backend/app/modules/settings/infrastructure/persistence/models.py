from datetime import datetime
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, Index, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime, UUIDPrimaryKey
from app.db.utils import generate_uuid


class PlatformSettingModel(Base):
    __tablename__ = "platform_settings"
    __table_args__ = (
        CheckConstraint(
            "scope IN ('system', 'organization')",
            name="ck_platform_settings_scope",
        ),
        CheckConstraint(
            "(scope = 'organization' AND organization_id IS NOT NULL) "
            "OR (scope = 'system' AND organization_id IS NULL)",
            name="ck_platform_settings_scope_org",
        ),
        Index("ix_platform_settings_scope_org", "scope", "organization_id"),
        Index("ix_platform_settings_key", "key"),
        Index(
            "uq_platform_settings_system_key",
            "key",
            unique=True,
            postgresql_where=sa.text("scope = 'system'"),
            sqlite_where=sa.text("scope = 'system'"),
        ),
        Index(
            "uq_platform_settings_org_key",
            "organization_id",
            "key",
            unique=True,
            postgresql_where=sa.text("scope = 'organization'"),
            sqlite_where=sa.text("scope = 'organization'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        UUIDPrimaryKey,
        primary_key=True,
        default=generate_uuid,
    )
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    organization_id: Mapped[UUID | None] = mapped_column(UUIDPrimaryKey, nullable=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[Any] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
