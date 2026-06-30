from datetime import datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db.types import UTCDateTime, UUIDPrimaryKey
from app.db.utils import generate_uuid


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for KYROX Core infrastructure models."""


class BaseModelMixin:
    """Reusable columns for Core persistence models.

    Provides UUID primary keys, UTC timestamps, and soft-delete support.
    Domain entities remain persistence-ignorant; infrastructure models inherit this mixin.
    """

    id: Mapped[UUID] = mapped_column(
        UUIDPrimaryKey,
        primary_key=True,
        default=generate_uuid,
    )
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
    deleted_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime,
        nullable=True,
        default=None,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
