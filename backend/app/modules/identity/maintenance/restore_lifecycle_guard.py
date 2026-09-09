"""Kyrox Core-owned lifecycle guard for destructive database restore.

The current Core database is authoritative immediately before a restore. This
module captures its organization lifecycle state into the caller's process memory,
then re-applies that state after pg_restore. The snapshot therefore survives the
database replacement without introducing a second authoritative database.

If the current Core database cannot be read, the snapshot is malformed, or the
restored backup is too old to contain an organization that exists in the current
snapshot, reconciliation fails closed.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.identity.domain.organization.enums.organization_status import OrganizationStatus
from app.modules.identity.infrastructure.organization.persistence.models.organization import (
    OrganizationModel,
)

SNAPSHOT_VERSION = 1
_ALLOWED_STATUSES = {status.value for status in OrganizationStatus}


@dataclass(frozen=True, slots=True)
class OrganizationLifecycleRestoreState:
    organization_id: UUID
    status: str
    deleted_at: datetime | None


@dataclass(frozen=True, slots=True)
class CoreLifecycleRestoreSnapshot:
    captured_at: datetime
    organizations: tuple[OrganizationLifecycleRestoreState, ...]
    version: int = SNAPSHOT_VERSION

    def to_json(self) -> str:
        payload = {
            "version": self.version,
            "captured_at": _format_datetime(self.captured_at),
            "organizations": [
                {
                    "organization_id": str(state.organization_id),
                    "status": state.status,
                    "deleted_at": _format_datetime(state.deleted_at),
                }
                for state in self.organizations
            ],
        }
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> "CoreLifecycleRestoreSnapshot":
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid Core lifecycle restore snapshot JSON") from exc
        if not isinstance(payload, dict) or payload.get("version") != SNAPSHOT_VERSION:
            raise ValueError("Unsupported Core lifecycle restore snapshot version")
        captured_at = _parse_datetime(payload.get("captured_at"), required=True)
        raw_states = payload.get("organizations")
        if not isinstance(raw_states, list):
            raise ValueError("Core lifecycle restore snapshot organizations must be a list")

        states: list[OrganizationLifecycleRestoreState] = []
        seen: set[UUID] = set()
        for item in raw_states:
            if not isinstance(item, dict):
                raise ValueError("Invalid organization lifecycle snapshot entry")
            try:
                organization_id = UUID(str(item.get("organization_id")))
            except (TypeError, ValueError, AttributeError) as exc:
                raise ValueError("Invalid organization_id in Core lifecycle snapshot") from exc
            if organization_id in seen:
                raise ValueError("Duplicate organization_id in Core lifecycle snapshot")
            seen.add(organization_id)
            status = item.get("status")
            if status not in _ALLOWED_STATUSES:
                raise ValueError("Invalid organization status in Core lifecycle snapshot")
            deleted_at = _parse_datetime(item.get("deleted_at"), required=False)
            states.append(
                OrganizationLifecycleRestoreState(
                    organization_id=organization_id,
                    status=str(status),
                    deleted_at=deleted_at,
                )
            )
        return cls(
            captured_at=captured_at,
            organizations=tuple(sorted(states, key=lambda state: str(state.organization_id))),
        )


@dataclass(frozen=True, slots=True)
class CoreLifecycleReconciliationResult:
    ok: bool
    organization_count: int
    lifecycle_reapplied_count: int
    resurrected_extra_tombstoned_count: int
    error_message: str | None = None

    def to_json(self) -> str:
        return json.dumps(
            {
                "ok": self.ok,
                "organization_count": self.organization_count,
                "lifecycle_reapplied_count": self.lifecycle_reapplied_count,
                "resurrected_extra_tombstoned_count": self.resurrected_extra_tombstoned_count,
                "error_message": self.error_message,
            },
            separators=(",", ":"),
            sort_keys=True,
        )


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: object, *, required: bool) -> datetime | None:
    if value is None:
        if required:
            raise ValueError("Core lifecycle restore snapshot is missing captured_at")
        return None
    if not isinstance(value, str):
        raise ValueError("Invalid datetime in Core lifecycle restore snapshot")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid datetime in Core lifecycle restore snapshot") from exc
    if parsed.tzinfo is None:
        raise ValueError("Core lifecycle restore snapshot datetimes must include timezone")
    return parsed.astimezone(UTC)


def capture_authoritative_lifecycle_snapshot(
    *,
    database_url: str,
    now: datetime | None = None,
) -> CoreLifecycleRestoreSnapshot:
    """Capture every current Core organization, including soft-deleted rows."""

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            models = session.scalars(select(OrganizationModel).order_by(OrganizationModel.id)).all()
            states = tuple(
                OrganizationLifecycleRestoreState(
                    organization_id=model.id,
                    status=model.status,
                    deleted_at=_normalize_datetime(model.deleted_at),
                )
                for model in models
            )
            for state in states:
                if state.status not in _ALLOWED_STATUSES:
                    raise ValueError(
                        f"Current Core contains invalid organization status for {state.organization_id}"
                    )
            captured_at = _normalize_datetime(now or datetime.now(tz=UTC))
            assert captured_at is not None
            return CoreLifecycleRestoreSnapshot(
                captured_at=captured_at,
                organizations=states,
            )
    except SQLAlchemyError as exc:
        raise ValueError("Could not capture current Core organization lifecycle authority") from exc
    finally:
        engine.dispose()


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def reconcile_restored_lifecycle_snapshot(
    *,
    database_url: str,
    snapshot: CoreLifecycleRestoreSnapshot,
) -> CoreLifecycleReconciliationResult:
    """Re-apply pre-restore Core lifecycle truth to the restored Core database.

    Rules:
    - an organization that exists now but is absent from the restored backup cannot
      be reconstructed safely, so certification blocks and no lifecycle mutation is
      committed;
    - an organization present only in the old backup is a resurrection candidate;
      it is soft-deleted at the snapshot capture time instead of becoming usable;
    - organizations present on both sides receive the current snapshot's status and
      deleted_at, preventing lifecycle rollback from the old backup.
    """

    authoritative = {state.organization_id: state for state in snapshot.organizations}
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            restored_models = session.scalars(
                select(OrganizationModel).order_by(OrganizationModel.id)
            ).all()
            restored = {model.id: model for model in restored_models}
            missing_from_backup = sorted(set(authoritative) - set(restored), key=str)
            if missing_from_backup:
                ids = ", ".join(str(value) for value in missing_from_backup)
                return CoreLifecycleReconciliationResult(
                    ok=False,
                    organization_count=len(authoritative),
                    lifecycle_reapplied_count=0,
                    resurrected_extra_tombstoned_count=0,
                    error_message=(
                        "Restored Core backup is missing organizations that exist in the "
                        f"pre-restore authoritative snapshot ({ids}); full state cannot be reconstructed"
                    ),
                )

            lifecycle_reapplied = 0
            resurrected_tombstoned = 0
            for organization_id, model in restored.items():
                state = authoritative.get(organization_id)
                if state is None:
                    # Old-only row: do not hard-delete without a durable hard-delete
                    # tombstone contract. Soft-delete it so it cannot resurrect.
                    model.status = OrganizationStatus.ARCHIVED.value
                    model.deleted_at = snapshot.captured_at
                    lifecycle_reapplied += 1
                    resurrected_tombstoned += 1
                    continue
                if model.status != state.status or _normalize_datetime(model.deleted_at) != state.deleted_at:
                    model.status = state.status
                    model.deleted_at = state.deleted_at
                    lifecycle_reapplied += 1

            session.commit()
            return CoreLifecycleReconciliationResult(
                ok=True,
                organization_count=len(authoritative),
                lifecycle_reapplied_count=lifecycle_reapplied,
                resurrected_extra_tombstoned_count=resurrected_tombstoned,
            )
    except SQLAlchemyError as exc:
        raise ValueError("Could not reconcile restored Core organization lifecycle authority") from exc
    finally:
        engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kyrox Core OL10 restore lifecycle guard")
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture_parser = subparsers.add_parser("capture")
    capture_parser.add_argument("--database-url", required=True)

    reconcile_parser = subparsers.add_parser("reconcile")
    reconcile_parser.add_argument("--database-url", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "capture":
            snapshot = capture_authoritative_lifecycle_snapshot(database_url=args.database_url)
            print(snapshot.to_json())
            return 0

        raw_snapshot = sys.stdin.read()
        snapshot = CoreLifecycleRestoreSnapshot.from_json(raw_snapshot)
        result = reconcile_restored_lifecycle_snapshot(
            database_url=args.database_url,
            snapshot=snapshot,
        )
        print(result.to_json())
        return 0 if result.ok else 2
    except ValueError as exc:
        print(json.dumps({"ok": False, "error_message": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
