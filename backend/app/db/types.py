"""Shared SQLAlchemy column types for infrastructure models."""

from sqlalchemy import DateTime, Uuid

UUIDPrimaryKey = Uuid(as_uuid=True)
UTCDateTime = DateTime(timezone=True)
