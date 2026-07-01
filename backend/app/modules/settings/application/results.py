from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SettingResult:
    id: UUID
    scope: str
    organization_id: UUID | None
    key: str
    value: Any
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class SettingListResult:
    items: list[SettingResult]
