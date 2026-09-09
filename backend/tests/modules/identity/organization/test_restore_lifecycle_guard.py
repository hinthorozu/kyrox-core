from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from app.modules.identity.domain.organization.enums.organization_status import OrganizationStatus
from app.modules.identity.infrastructure.organization.persistence.models.organization import (
    OrganizationModel,
)
from app.modules.identity.maintenance.restore_lifecycle_guard import (
    CoreLifecycleRestoreSnapshot,
    capture_authoritative_lifecycle_snapshot,
    reconcile_restored_lifecycle_snapshot,
)


def _database_url(tmp_path: Path) -> str:
    return f"sqlite+pysqlite:///{tmp_path / 'core.db'}"


def _create_schema(database_url: str) -> None:
    engine = create_engine(database_url)
    OrganizationModel.__table__.create(engine)
    engine.dispose()


def _add_organization(
    database_url: str,
    *,
    organization_id: UUID,
    slug: str,
    status: str,
    deleted_at: datetime | None = None,
) -> None:
    engine = create_engine(database_url)
    with Session(engine) as session:
        session.add(
            OrganizationModel(
                id=organization_id,
                name=f"Organization {slug}",
                slug=slug,
                status=status,
                deleted_at=deleted_at,
            )
        )
        session.commit()
    engine.dispose()


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def test_snapshot_round_trip_includes_soft_deleted_organizations(tmp_path: Path) -> None:
    database_url = _database_url(tmp_path)
    _create_schema(database_url)
    active_id = uuid4()
    deleted_id = uuid4()
    deleted_at = datetime(2026, 9, 1, 10, 30, tzinfo=UTC)
    _add_organization(
        database_url,
        organization_id=active_id,
        slug="active",
        status=OrganizationStatus.ACTIVE.value,
    )
    _add_organization(
        database_url,
        organization_id=deleted_id,
        slug="deleted",
        status=OrganizationStatus.ARCHIVED.value,
        deleted_at=deleted_at,
    )

    snapshot = capture_authoritative_lifecycle_snapshot(
        database_url=database_url,
        now=datetime(2026, 9, 9, 12, 0, tzinfo=UTC),
    )
    round_tripped = CoreLifecycleRestoreSnapshot.from_json(snapshot.to_json())

    assert {state.organization_id for state in round_tripped.organizations} == {
        active_id,
        deleted_id,
    }
    deleted_state = next(
        state for state in round_tripped.organizations if state.organization_id == deleted_id
    )
    assert deleted_state.status == OrganizationStatus.ARCHIVED.value
    assert deleted_state.deleted_at == deleted_at


def test_reconcile_reapplies_current_lifecycle_and_tombstones_old_only_rows(
    tmp_path: Path,
) -> None:
    database_url = _database_url(tmp_path)
    _create_schema(database_url)
    active_id = uuid4()
    deleted_id = uuid4()
    resurrected_old_id = uuid4()
    deleted_at = datetime(2026, 9, 2, 8, 0, tzinfo=UTC)
    captured_at = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)

    _add_organization(
        database_url,
        organization_id=active_id,
        slug="active",
        status=OrganizationStatus.ACTIVE.value,
    )
    _add_organization(
        database_url,
        organization_id=deleted_id,
        slug="deleted",
        status=OrganizationStatus.ARCHIVED.value,
        deleted_at=deleted_at,
    )
    snapshot = capture_authoritative_lifecycle_snapshot(
        database_url=database_url,
        now=captured_at,
    )

    # Simulate an older Core backup being restored: a deleted org becomes active,
    # and an organization absent from current Core reappears from old history.
    engine = create_engine(database_url)
    with Session(engine) as session:
        deleted_model = session.get(OrganizationModel, deleted_id)
        assert deleted_model is not None
        deleted_model.status = OrganizationStatus.ACTIVE.value
        deleted_model.deleted_at = None
        session.add(
            OrganizationModel(
                id=resurrected_old_id,
                name="Old Organization",
                slug="old-only",
                status=OrganizationStatus.ACTIVE.value,
            )
        )
        session.commit()
    engine.dispose()

    result = reconcile_restored_lifecycle_snapshot(
        database_url=database_url,
        snapshot=snapshot,
    )

    assert result.ok is True
    assert result.lifecycle_reapplied_count == 2
    assert result.resurrected_extra_tombstoned_count == 1

    engine = create_engine(database_url)
    with Session(engine) as session:
        deleted_model = session.get(OrganizationModel, deleted_id)
        assert deleted_model is not None
        assert deleted_model.status == OrganizationStatus.ARCHIVED.value
        assert _as_utc(deleted_model.deleted_at) == deleted_at

        resurrected = session.get(OrganizationModel, resurrected_old_id)
        assert resurrected is not None
        assert resurrected.status == OrganizationStatus.ARCHIVED.value
        assert _as_utc(resurrected.deleted_at) == captured_at
    engine.dispose()


def test_reconcile_blocks_if_backup_cannot_reconstruct_current_organization(
    tmp_path: Path,
) -> None:
    database_url = _database_url(tmp_path)
    _create_schema(database_url)
    current_id = uuid4()
    other_id = uuid4()
    _add_organization(
        database_url,
        organization_id=current_id,
        slug="current",
        status=OrganizationStatus.ACTIVE.value,
    )
    _add_organization(
        database_url,
        organization_id=other_id,
        slug="other",
        status=OrganizationStatus.SUSPENDED.value,
    )
    snapshot = capture_authoritative_lifecycle_snapshot(
        database_url=database_url,
        now=datetime(2026, 9, 9, 12, 0, tzinfo=UTC),
    )

    # Simulate backup taken before current_id existed. Also regress other_id;
    # the failed reconciliation must not commit that unrelated lifecycle mutation.
    engine = create_engine(database_url)
    with Session(engine) as session:
        session.execute(delete(OrganizationModel).where(OrganizationModel.id == current_id))
        other = session.get(OrganizationModel, other_id)
        assert other is not None
        other.status = OrganizationStatus.ACTIVE.value
        session.commit()
    engine.dispose()

    result = reconcile_restored_lifecycle_snapshot(
        database_url=database_url,
        snapshot=snapshot,
    )

    assert result.ok is False
    assert str(current_id) in (result.error_message or "")

    engine = create_engine(database_url)
    with Session(engine) as session:
        other = session.scalar(select(OrganizationModel).where(OrganizationModel.id == other_id))
        assert other is not None
        assert other.status == OrganizationStatus.ACTIVE.value
    engine.dispose()
