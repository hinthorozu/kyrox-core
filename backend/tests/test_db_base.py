import uuid

from sqlalchemy import DateTime, Uuid, inspect

from app.db.base import Base, BaseModelMixin
from app.db.utils import generate_uuid


class _SampleRecord(BaseModelMixin, Base):
    __tablename__ = "test_sample_records"


def test_base_model_mixin_exposes_expected_columns() -> None:
    columns = {column.key for column in inspect(_SampleRecord).columns}

    assert columns == {"id", "created_at", "updated_at", "deleted_at"}


def test_base_model_mixin_column_types() -> None:
    table = _SampleRecord.__table__

    assert isinstance(table.c.id.type, Uuid)
    assert table.c.id.type.as_uuid is True
    assert table.c.id.primary_key is True
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    assert isinstance(table.c.updated_at.type, DateTime)
    assert table.c.updated_at.type.timezone is True
    assert isinstance(table.c.deleted_at.type, DateTime)
    assert table.c.deleted_at.type.timezone is True
    assert table.c.deleted_at.nullable is True


def test_generate_uuid_returns_uuid() -> None:
    value = generate_uuid()

    assert isinstance(value, uuid.UUID)


def test_base_model_mixin_soft_delete_flag_defaults_false() -> None:
    record = _SampleRecord()

    assert record.is_deleted is False
    assert record.deleted_at is None
